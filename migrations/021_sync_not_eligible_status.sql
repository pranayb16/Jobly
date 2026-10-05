-- ============================================================
-- Sync visible enrichment status with AI eligibility
--
-- Jobs that should not receive AI enrichment should display
-- classification_status = 'not_eligible'.
--
-- Existing enrichment records in job_enrichments are preserved.
-- ============================================================


-- ------------------------------------------------------------
-- NON-US JOBS
-- ------------------------------------------------------------

UPDATE jobs
SET
    classification_status = 'not_eligible',
    enrichment_eligibility = 'not_eligible',
    enrichment_eligibility_reason = 'non_us',
    classification_started_at = NULL,
    classification_error = NULL
WHERE is_us_job = FALSE;


-- ------------------------------------------------------------
-- JOBS OLDER THAN 15 DAYS
--
-- Non-US reason takes precedence if both conditions apply.
-- ------------------------------------------------------------

UPDATE jobs
SET
    classification_status = 'not_eligible',
    enrichment_eligibility = 'not_eligible',
    enrichment_eligibility_reason = 'older_than_15_days',
    classification_started_at = NULL,
    classification_error = NULL
WHERE is_us_job IS DISTINCT FROM FALSE
  AND posted_at IS NOT NULL
  AND posted_at < NOW() - INTERVAL '15 days';


-- ------------------------------------------------------------
-- CURRENT QUEUE ROWS
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
  AND j.classification_status = 'not_eligible'
  AND q.status <> 'not_eligible';