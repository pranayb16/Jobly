# Jobly

Jobly collects public job postings from Greenhouse, Ashby, and Lever, normalizes them,
keeps source and crawl history in PostgreSQL, conservatively identifies U.S. roles,
enriches fresh eligible jobs with Gemini, and publishes ready jobs through FastAPI to a
Next.js frontend. The public product remains a rolling 48-hour job index.

## Architecture

```text
ATS APIs -> crawl command -> PostgreSQL/Cloud SQL -> enrich command -> public_jobs
                                                                  -> FastAPI
                                                                  -> Next.js
```

The crawler and enrichment worker each run once and exit. `pipeline` runs them in order.
Cloud Scheduler, rather than application sleeps, owns the production schedule.

## Repository layout

```text
backend/       installable jobly package, API, workers, commands, tests, Dockerfile
frontend/      existing Next.js application and server-side FastAPI proxy
migrations/    ordered PostgreSQL migrations and publication views
scripts/       development and one-off maintenance utilities
data/          source-discovery datasets (not included in the Python package)
infra/gcp/     deployment architecture and command outline
.github/       backend and frontend verification workflows
```

## Local setup

Python 3.11+ and Node.js 22 are supported. PostgreSQL is required for migrations and all
runtime commands except `--help` and deterministic unit tests.

```bash
cp .env.example .env
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Install the frontend separately:

```bash
cd frontend
npm ci
cp .env.local.example .env.local
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string; required when database work begins | none |
| `FRONTEND_ORIGIN` | Allowed browser origin for FastAPI CORS | `http://localhost:3000` |
| `GEMINI_API_KEY` | Gemini credential; required only by enrichment | none |
| `AI_MODEL` | Gemini model | `gemini-3.5-flash-lite` |
| `AI_CLASSIFICATION_VERSION` | Stored classifier version | `v1` |
| `AI_MAX_ATTEMPTS` | Maximum AI attempts before failure | `5` |
| `CRAWL_SOURCE_LIMIT` | Maximum active sources per run; blank means all | blank |
| `APP_ENV` | Environment label | `development` |
| `LOG_LEVEL` | stdout logging level | `INFO` |

The conservative drop guard also accepts `CRAWL_MASS_DROP_MIN_PREVIOUS_JOBS` (default
`20`) and `CRAWL_MASS_DROP_RATIO` (default `0.25`). Production should inject secrets from
Secret Manager; it does not need a `.env` file.

## Database and runtime commands

Run these from `backend/` with the package installed:

```bash
python -m jobly.commands.migrate
python -m jobly.commands.seed_sources
python -m jobly.commands.crawl
python -m jobly.commands.enrich --limit 10
python -m jobly.commands.pipeline --enrichment-limit 10
uvicorn jobly.api.main:app --reload --host 0.0.0.0 --port 8000
```

The migration runner creates `schema_migrations` and applies each numbered SQL file once.
It preserves the existing schema and ordered history. The crawler records individual
source failures and continues; fatal configuration or database failures return non-zero.

The API contract remains:

- `GET /health`
- `GET /api/jobs?limit=20&offset=0`
- `GET /api/jobs/{job_id}`

Only `public_jobs` is exposed. Non-U.S. jobs remain stored internally and do not consume
Gemini work; ambiguous `Remote` alone is not U.S. evidence.

## Frontend

Set `frontend/.env.local`:

```env
JOBS_API_URL=http://localhost:8000
USE_MOCK_DATA=false
```

Then run:

```bash
cd frontend
npm run dev
```

`JOBS_API_URL` is read only by the Next.js server proxy. Existing filters, API
normalization, visibility refresh, and polling behavior are unchanged.

## Tests and checks

```bash
cd backend
pytest
ruff check .

# Optional live calls to external ATS APIs
pytest -m integration

cd ../frontend
npm run check
npm run build
```

Unit tests use sanitized fixtures and do not need network access. Live ATS tests are
marked `integration` and excluded from standard CI.

## Docker

```bash
docker build -t jobly-backend ./backend
docker run --rm -p 8080:8080 \
  --env-file .env \
  jobly-backend
```

The image runs as a non-root user and defaults to FastAPI. Override the command for jobs:

```bash
docker run --rm --env-file .env jobly-backend python -m jobly.commands.crawl
docker run --rm --env-file .env jobly-backend python -m jobly.commands.enrich --limit 10
docker run --rm --env-file .env jobly-backend python -m jobly.commands.pipeline
```

## Production outline

- Vercel hosts `frontend/` and sets `JOBS_API_URL` to the FastAPI service URL.
- A Cloud Run service runs the image's default FastAPI command.
- A Cloud Run job overrides the command with `python -m jobly.commands.pipeline`.
- Cloud SQL for PostgreSQL remains the source of truth.
- Cloud Scheduler invokes the job at 09:00, 12:00, 14:00, and 16:00 in
  `America/Chicago`.
- Secret Manager supplies `DATABASE_URL` and `GEMINI_API_KEY`.

See [infra/gcp/README.md](infra/gcp/README.md) for deployment commands. Terraform and
automatic deployment are intentionally deferred.

## Maintenance scripts

`scripts/clean_sources.py`, `scripts/validate_sources.py`, and
`scripts/backfill_us_market.py` are explicit maintenance operations. `scripts/dev_soak.py`
is a local-only soak utility with a sleeping loop; it is not part of production scheduling.
