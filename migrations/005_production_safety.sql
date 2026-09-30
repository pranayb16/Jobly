-- Record successful crawls whose results were retained but not used for deactivation.
ALTER TABLE crawl_runs
ADD COLUMN IF NOT EXISTS deactivation_skipped BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE crawl_runs
ADD COLUMN IF NOT EXISTS warning TEXT;
