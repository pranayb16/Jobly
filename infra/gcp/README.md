# Jobly on GCP

## Intended architecture

```text
Vercel (Next.js)
    -> Cloud Run service (FastAPI)
       -> Cloud SQL for PostgreSQL

Cloud Scheduler
    -> Cloud Run job (crawl then enrich)
       -> Cloud SQL for PostgreSQL
       -> Gemini API
```

The API and pipeline use the same backend image. The service keeps the image's default
Uvicorn command; the job overrides it with `python -m jobly.commands.pipeline`.

## Build and publish

Choose a project, region, Artifact Registry repository, and Cloud SQL instance first.

```bash
gcloud builds submit backend \
  --tag us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG
```

## Deploy the API service

Store `DATABASE_URL` in Secret Manager. Attach the Cloud SQL instance when the URL uses
its Unix socket. Keep non-secret configuration as environment variables.

```bash
gcloud run deploy jobly-api \
  --image us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG \
  --region us-central1 \
  --port 8080 \
  --add-cloudsql-instances PROJECT_ID:us-central1:INSTANCE \
  --set-secrets DATABASE_URL=jobly-database-url:latest \
  --set-env-vars APP_ENV=production,LOG_LEVEL=INFO,FRONTEND_ORIGIN=https://YOUR_FRONTEND_HOST
```

Set Vercel's server-side `JOBS_API_URL` to the resulting Cloud Run service URL.

## Deploy the pipeline job

Store both `DATABASE_URL` and `GEMINI_API_KEY` in Secret Manager.

```bash
gcloud run jobs deploy jobly-pipeline \
  --image us-central1-docker.pkg.dev/PROJECT_ID/jobly/jobly-backend:TAG \
  --region us-central1 \
  --command python \
  --args=-m,jobly.commands.pipeline \
  --add-cloudsql-instances PROJECT_ID:us-central1:INSTANCE \
  --set-secrets DATABASE_URL=jobly-database-url:latest,GEMINI_API_KEY=jobly-gemini-api-key:latest \
  --set-env-vars APP_ENV=production,LOG_LEVEL=INFO,AI_MODEL=gemini-3.5-flash-lite,AI_CLASSIFICATION_VERSION=v1,AI_MAX_ATTEMPTS=5,CRAWL_SOURCE_LIMIT=50 \
  --task-timeout 3600s \
  --max-retries 1
```

Execute it manually for a smoke test:

```bash
gcloud run jobs execute jobly-pipeline --region us-central1 --wait
```

## Schedule

Cloud Scheduler owns the schedule; the Python processes run once and exit. Grant the
scheduler service account permission to run the Cloud Run job, then create one schedule
covering the four desired local times:

```bash
gcloud scheduler jobs create http jobly-pipeline-schedule \
  --location us-central1 \
  --schedule "0 9,12,14,16 * * *" \
  --time-zone "America/Chicago" \
  --uri "https://run.googleapis.com/v2/projects/PROJECT_ID/locations/us-central1/jobs/jobly-pipeline:run" \
  --http-method POST \
  --oauth-service-account-email jobly-scheduler@PROJECT_ID.iam.gserviceaccount.com
```

Use Secret Manager/environment injection for secrets; do not bake `.env` files or
credentials into the image. Apply database migrations before switching traffic to code
that depends on them. No infrastructure is created automatically by this repository.

References: [Cloud Run services](https://cloud.google.com/run/docs/deploying),
[Cloud Run jobs](https://cloud.google.com/run/docs/create-jobs), and
[authenticated Scheduler targets](https://cloud.google.com/scheduler/docs/http-target-auth).
