# Jobly

Jobly is a hiring-intelligence platform. Once per day it crawls employer career sites,
stores the current job state, preserves prior versions and lifecycle events, processes a
bounded AI enrichment queue, and creates deterministic company snapshots. The original
48-hour job-search product remains available under `/jobs` and `/api/jobs`.

## Architecture

```text
Cloud Scheduler (once/day)
  -> pipeline_run
  -> migrate
  -> source_candidates -> validated sources
  -> crawl ATS sites
       -> jobs (current state)
       -> job_versions + job_events (history)
       -> enrichment_queue (new/changed first)
  -> bounded OpenRouter v3 enrichment -> job_enrichments.data
  -> company_daily_snapshots
  -> deterministic intelligence API -> Next.js intelligence routes
```

The crawler never calls OpenRouter. A remaining enrichment backlog is recorded but does not
fail ingestion or snapshot generation.

## Repository layout

```text
backend/jobly/companies/      canonical company identity and conservative linking
backend/jobly/products/jobs/ optional legacy job-board API
backend/jobly/enrichment/     deterministic extraction, versioned schemas, queue worker
backend/jobly/intelligence/   daily snapshots and deterministic trend queries
backend/jobly/pipeline/       pipeline-run persistence
frontend/app/                 intelligence routes plus the existing /jobs experience
migrations/                   ordered PostgreSQL schema migrations
data/                         CSV import sources; not a production runtime dependency
infra/gcp/                    Cloud Run and once-daily Scheduler instructions
```

## Local setup

Python 3.11+, Node.js 22, and PostgreSQL are required.

```bash
cp .env.example .env
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

cd ../frontend
npm ci
cp .env.local.example .env.local
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | none |
| `FRONTEND_ORIGIN` | Allowed browser origin | `http://localhost:3000` |
| `ADMIN_API_TOKEN` | Bearer token required by `/api/admin/runs*` | none; admin API fails closed |
| `OPENROUTER_API_KEY` | Required only by the enrichment worker | none |
| `OPENROUTER_FREE_MODEL` | Free-first OpenRouter model | `openai/gpt-oss-20b:free` |
| `OPENROUTER_PAID_MODEL` | Paid fallback OpenRouter model | `openai/gpt-oss-20b` |
| `OPENROUTER_PAID_PROVIDERS` | Ordered paid-provider allowlist | `coreweave,deepinfra,akashml` |
| `AI_CLASSIFICATION_VERSION` | Rich output schema version | `v3` |
| `AI_PROMPT_VERSION` | Persisted prompt version | `v3` |
| `AI_MAX_ATTEMPTS` | Queue retries before terminal failure | `5` |
| `AI_ENRICHMENT_LIMIT` | Maximum AI classification attempts per pipeline run | `5000` |
| `SOURCE_TARGET_COUNT` | Desired active validated source inventory | `1000` |
| `CRAWL_SOURCE_LIMIT` | Optional development/debug crawl cap | blank (all active sources) |
| `APP_ENV` | Environment label | `development` |
| `LOG_LEVEL` | stdout log level | `INFO` |

The mass-drop guard also accepts `CRAWL_MASS_DROP_MIN_PREVIOUS_JOBS` (default `20`)
and `CRAWL_MASS_DROP_RATIO` (default `0.25`). An anomalous crawl is recorded in
`crawl_runs`, but its count never replaces `sources.last_job_count` as the trusted
baseline.

## Database migrations

From `backend/` with `DATABASE_URL` configured:

```bash
python -m jobly.commands.migrate
```

Migrations are ordered and idempotently recorded in `schema_migrations`. The new schema
adds canonical companies, job versions/events, the enrichment queue, rich JSONB
enrichments, daily company snapshots, pipeline runs, and database-backed source
candidates. The legacy `jobs.company`, v1 columns, and `public_jobs` view remain.

## First production bootstrap

CSV files are one-time import inputs only. Production source reconciliation reads
`source_candidates` from PostgreSQL.

```bash
cd backend
python -m jobly.commands.migrate
python -m jobly.commands.import_source_candidates \
  --input ../data/cleaned/valid_sources.csv
python -m jobly.commands.sync_sources --target 1000
python -m jobly.commands.crawl
python -m jobly.commands.bootstrap_enrichment
python -m jobly.commands.enrich --limit 5000
python -m jobly.commands.snapshot
```

`bootstrap_enrichment` is idempotent and does not call OpenRouter. New and changed jobs
already have priorities 1 and 2; existing backlog receives priority 3.

## Daily pipeline

```bash
cd backend
python -m jobly.commands.pipeline
```

Useful development overrides:

```bash
python -m jobly.commands.pipeline \
  --source-target 25 \
  --source-limit 5 \
  --enrichment-limit 20
```

The source target controls inventory reconciliation. The source limit controls only how
many active sources this crawl executes. If the target is below the current active count,
Jobly logs a warning and does not disable or delete sources.

## APIs and frontend

Core intelligence endpoints:

- `GET /api/companies` and `GET /api/companies/{slug}`
- `GET /api/companies/{slug}/trends`
- `GET /api/trends`
- `GET /api/roles` and `GET /api/roles/{role}`
- `GET /api/skills` and `GET /api/skills/{skill}`

Job-board compatibility endpoints remain `GET /api/jobs` and `GET /api/jobs/{job_id}`.
Health endpoints are `/health`, `/health/live`, `/health/ready`, and `/health/system`.
Low-coverage semantic aggregates are returned as unavailable rather than presented as a
complete-market conclusion.

The frontend uses `JOBS_API_URL` for both intelligence and job APIs. Routes are `/`,
`/companies`, `/companies/[slug]`, `/roles`, `/roles/[role]`, `/skills`,
`/skills/[skill]`, `/trends`, and `/jobs`.

## Tests and checks

```bash
cd backend
pytest
ruff check .

cd ../frontend
npm run check
npm run build
```

Live ATS integration tests remain marked `integration` and are excluded by default.

## Docker

The backend image must be built from the repository root so it contains both the package
and root migrations:

```bash
docker build -f backend/Dockerfile -t jobly-backend .
docker run --rm --env-file .env jobly-backend \
  python -m jobly.commands.migrate
docker run --rm --env-file .env jobly-backend \
  python -m jobly.commands.pipeline
```

The default container command serves FastAPI on port 8080. See
[`infra/gcp/README.md`](infra/gcp/README.md) for the Cloud Run deployment and one daily
Scheduler execution in `America/Chicago`.

## Intentionally deferred

Adaptive or multiple-daily crawling, AI-generated predictions, payments, resumes,
auto-apply, recommendations, MCP, and alerts are outside this iteration. The first trend
API is deterministic and reports unavailable periods when 7 or 30 days of history do not
exist.
