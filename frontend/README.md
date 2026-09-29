# Jobly

A modern job board built with Next.js, React, and TypeScript. A server-only Next.js route proxies the FastAPI jobs service, so backend configuration never reaches the browser.

## Run locally

1. Install dependencies:

   ```bash
   npm install
   ```

2. Copy the environment template:

   ```bash
   cp .env.local.example .env.local
   ```

3. Set `JOBS_API_URL` in `.env.local` to your FastAPI base URL. For local development:

   ```env
   JOBS_API_URL=http://localhost:8000
   ```

4. Start Next.js:

   ```bash
   npm run dev
   ```

Open `http://localhost:3000`.

For a UI preview without FastAPI, set `USE_MOCK_DATA=true` in `.env.local`.

## FastAPI contract

The frontend requests the paginated `GET /api/jobs` endpoint through its own `/api/jobs` proxy. It keeps only roles posted within the last 48 hours, stops paging once it reaches older results, and enriches each fresh role from `GET /api/jobs/{job_id}` so the cards can show `description_text`. It understands these common response fields:

| Website field | Recognized API fields |
| --- | --- |
| Title | `title`, `job_title`, `position` |
| Company | `company`, `company_name`, `organization` |
| Location | `location`, `job_location`, `city` |
| Description | `description`, `job_description`, `summary` |
| Employment type | `employment_type`, `job_type`, `type` |
| Workplace type | `workplace_type`, `work_mode`, `remote_type` |
| Salary | `salary_min` / `salary_max`, or `min_salary` / `max_salary` |
| Date | `posted_at`, `created_at`, `date_posted` |

Only the Next.js server reads `JOBS_API_URL`; the browser uses the same-origin `/api/jobs` route.

## Production

```bash
npm run build
npm start
```

Next.js serves both the website and `/api/jobs` on port `3000` by default.
