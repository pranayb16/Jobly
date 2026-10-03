# Jobly on GCP

## Intended architecture

```text
Vercel (Next.js intelligence UI)
  -> Cloud Run service (FastAPI)
     -> Cloud SQL for PostgreSQL

Cloud Scheduler (once/day, America/Chicago)
  -> Cloud Run job (daily pipeline)
     -> ATS APIs + Cloud SQL + bounded Gemini work
```

The API and pipeline use the same image. Build from the repository root so
`/app/migrations` exists in the container.

## Build and publish

Build and push with Docker from the repository root:

```bash
docker build -f backend/Dockerfile \
  -t us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG .
docker push us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG
```

## Deploy the API

```bash
gcloud run deploy jobly-api \
  --image us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG \
  --region us-central1 \
  --port 8080 \
  --add-cloudsql-instances PROJECT_ID:us-central1:INSTANCE \
  --set-secrets DATABASE_URL=jobly-database-url:latest \
  --set-env-vars APP_ENV=production,LOG_LEVEL=INFO,FRONTEND_ORIGIN=https://YOUR_FRONTEND_HOST,SOURCE_TARGET_COUNT=1000
```

Set Vercel's server-only `JOBS_API_URL` to the resulting service URL.

## Deploy the daily pipeline job

```bash
gcloud run jobs deploy jobly-pipeline \
  --image us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG \
  --region us-central1 \
  --command python \
  --args=-m,jobly.commands.pipeline \
  --add-cloudsql-instances PROJECT_ID:us-central1:INSTANCE \
  --set-secrets DATABASE_URL=jobly-database-url:latest,GEMINI_API_KEY=jobly-gemini-api-key:latest \
  --set-env-vars APP_ENV=production,LOG_LEVEL=INFO,AI_MODEL=gemini-3.5-flash-lite,AI_CLASSIFICATION_VERSION=v2,AI_PROMPT_VERSION=v2,AI_MAX_ATTEMPTS=5,AI_ENRICHMENT_LIMIT=5000,SOURCE_TARGET_COUNT=1000 \
  --task-timeout 86400s \
  --max-retries 1
```

Do not set `CRAWL_SOURCE_LIMIT` in production. It is only a development/debug cap.

Before the first pipeline run, use one-off Cloud Run jobs based on the same image to run
`python -m jobly.commands.migrate` and then
`python -m jobly.commands.import_source_candidates`. The image contains the verified CSV
only for that import command; all subsequent reconciliation reads PostgreSQL. After the
first crawl, run `python -m jobly.commands.bootstrap_enrichment` once for any pre-existing
jobs. The exact command order is in the root README.

After bootstrap, execute the daily job manually as a smoke test:

```bash
gcloud run jobs execute jobly-pipeline --region us-central1 --wait
```

## Once-daily schedule

Grant the scheduler service account permission to run the Cloud Run job, then create one
execution per day at 09:00 local time:

```bash
gcloud scheduler jobs create http jobly-pipeline-daily \
  --location us-central1 \
  --schedule "0 9 * * *" \
  --time-zone "America/Chicago" \
  --uri "https://run.googleapis.com/v2/projects/PROJECT_ID/locations/us-central1/jobs/jobly-pipeline:run" \
  --http-method POST \
  --oauth-service-account-email jobly-scheduler@PROJECT_ID.iam.gserviceaccount.com
```

Use Secret Manager for credentials. A remaining enrichment backlog is expected and does
not fail the daily job; inspect `/health/system` and `pipeline_runs` for operational
status. Adaptive and multiple-daily schedules are intentionally deferred.
