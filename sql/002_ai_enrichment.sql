-- ============================================================
-- Jobly AI enrichment migration
-- ============================================================

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS content_hash TEXT;


-- ------------------------------------------------------------
-- Classification state
-- ------------------------------------------------------------

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_status TEXT
NOT NULL DEFAULT 'pending';

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_started_at TIMESTAMPTZ;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_attempts INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_error TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_version TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classified_at TIMESTAMPTZ;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classified_content_hash TEXT;


-- ------------------------------------------------------------
-- AI-generated searchable fields
-- ------------------------------------------------------------

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS job_family TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS job_subfamily TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS related_roles JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS skills JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS seniority TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS years_experience_min INTEGER;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS years_experience_max INTEGER;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS ai_locations JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS classification_confidence REAL;


-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS jobs_classification_pending_idx
ON jobs (classification_status, id)
WHERE classification_status IN ('pending', 'processing');


CREATE INDEX IF NOT EXISTS jobs_public_ready_idx
ON jobs (posted_at DESC)
WHERE active = TRUE
  AND classification_status = 'ready';


-- ------------------------------------------------------------
-- Public publication gate
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW public_jobs AS

SELECT *
FROM jobs

WHERE active = TRUE

  AND classification_status = 'ready'

  AND content_hash IS NOT NULL

  AND classified_content_hash = content_hash

  AND posted_at IS NOT NULL

  AND posted_at >= NOW() - INTERVAL '48 hours';