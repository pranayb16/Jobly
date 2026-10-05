-- ============================================================
-- Jobly AI enrichment window: 7 days
--
-- AI enrichment is restricted to jobs posted within
-- the last 7 days.
--
-- Non-U.S. jobs remain not eligible.
-- Jobs without posted_at remain eligible for now.
-- ============================================================


-- ------------------------------------------------------------
-- UPDATE JOB ELIGIBILITY
-- ------------------------------------------------------------

UPDATE jobs
SET
    enrichment_eligibility =
        CASE
            WHEN is_us_job = FALSE
                THEN 'not_eligible'

            WHEN posted_at IS NOT NULL
             AND posted_at < NOW() - INTERVAL '7 days'
                THEN 'not_eligible'

            ELSE 'eligible'
        END,

    enrichment_eligibility_reason =
        CASE
            WHEN is_us_job = FALSE
                THEN 'non_us'

            WHEN posted_at IS NOT NULL
             AND posted_at < NOW() - INTERVAL '7 days'
                THEN 'older_than_7_days'

            ELSE NULL
        END;


-- ------------------------------------------------------------
-- SYNC VISIBLE CLASSIFICATION STATUS
--
-- Existing enrichment rows in job_enrichments are preserved.
-- We only change the current visible status.
-- ------------------------------------------------------------

UPDATE jobs
SET
    classification_status = 'not_eligible',
    classification_started_at = NULL,
    classification_error = NULL
WHERE enrichment_eligibility = 'not_eligible';


-- ------------------------------------------------------------
-- SYNC CURRENT ENRICHMENT QUEUE
-- ------------------------------------------------------------

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