-- ============================================================
-- Jobly AI enrichment eligibility
--
-- Keep AI processing state separate from AI eligibility.
--
-- classification_status:
--   pending / processing / ready / skipped_non_us / failed
--
-- enrichment_eligibility:
--   eligible / not_eligible
--
-- Current not-eligible rules:
--   1. Known non-U.S. job
--   2. Exact posted_at is older than 15 days
--
-- Jobs without posted_at remain eligible for now.
-- Their observation/baseline behavior will be handled separately.
-- ============================================================


-- ============================================================
-- JOB ELIGIBILITY
-- ============================================================

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS enrichment_eligibility TEXT
NOT NULL DEFAULT 'eligible';


ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS enrichment_eligibility_reason TEXT;


ALTER TABLE jobs
DROP CONSTRAINT IF EXISTS jobs_enrichment_eligibility_check;


ALTER TABLE jobs
ADD CONSTRAINT jobs_enrichment_eligibility_check
CHECK (
    enrichment_eligibility IN (
        'eligible',
        'not_eligible'
    )
);


-- ============================================================
-- QUEUE STATUS
--
-- Queue rows should also be able to say "not_eligible"
-- instead of pretending that an intentionally skipped job
-- was successfully AI-completed.
-- ============================================================

ALTER TABLE enrichment_queue
DROP CONSTRAINT IF EXISTS enrichment_queue_status_check;


ALTER TABLE enrichment_queue
ADD CONSTRAINT enrichment_queue_status_check
CHECK (
    status IN (
        'pending',
        'processing',
        'completed',
        'failed',
        'not_eligible'
    )
);


-- ============================================================
-- BACKFILL JOB ELIGIBILITY
--
-- Non-U.S. takes precedence as the reason if a job is both
-- non-U.S. and older than 15 days.
-- ============================================================

UPDATE jobs
SET
    enrichment_eligibility =
        CASE
            WHEN is_us_job = FALSE
                THEN 'not_eligible'

            WHEN posted_at IS NOT NULL
             AND posted_at < NOW() - INTERVAL '15 days'
                THEN 'not_eligible'

            ELSE 'eligible'
        END,

    enrichment_eligibility_reason =
        CASE
            WHEN is_us_job = FALSE
                THEN 'non_us'

            WHEN posted_at IS NOT NULL
             AND posted_at < NOW() - INTERVAL '15 days'
                THEN 'older_than_15_days'

            ELSE NULL
        END;


-- ============================================================
-- CURRENT QUEUE ROWS
--
-- Current-content queue rows belonging to jobs that are now
-- not eligible should no longer appear as pending/completed.
-- ============================================================

UPDATE enrichment_queue AS q
SET
    status = 'not_eligible',
    started_at = NULL,
    completed_at = NOW(),
    last_error = NULL

FROM jobs AS j

WHERE q.job_id = j.id

  AND q.content_hash = j.content_hash

  AND j.enrichment_eligibility = 'not_eligible'

  AND q.status <> 'not_eligible';


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS jobs_enrichment_eligibility_idx
ON jobs (
    enrichment_eligibility,
    posted_at
);


CREATE INDEX IF NOT EXISTS enrichment_queue_not_eligible_idx
ON enrichment_queue (
    status,
    job_id
)
WHERE status = 'not_eligible';