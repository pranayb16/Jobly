-- Restrict AI enrichment to jobs with a known posting time in the last day.

UPDATE jobs
SET
    enrichment_eligibility = 'not_eligible',
    enrichment_eligibility_reason = CASE
        WHEN posted_at IS NULL THEN 'missing_posted_at'
        ELSE 'older_than_1_day'
    END,
    classification_status = CASE
        WHEN classification_status IN ('pending', 'processing')
            THEN 'not_eligible'
        ELSE classification_status
    END,
    classification_started_at = NULL
WHERE (posted_at IS NULL OR posted_at < NOW() - INTERVAL '1 day')
  AND (
      enrichment_eligibility = 'eligible'
      OR classification_status IN ('pending', 'processing')
  );


UPDATE enrichment_queue AS q
SET
    status = 'not_eligible',
    started_at = NULL,
    completed_at = NOW(),
    next_attempt_at = NULL,
    last_error = CASE
        WHEN j.posted_at IS NULL THEN 'missing_posted_at'
        ELSE 'older_than_1_day'
    END
FROM jobs AS j
WHERE q.job_id = j.id
  AND q.content_hash = j.content_hash
  AND q.status IN ('pending', 'processing')
  AND (j.posted_at IS NULL OR j.posted_at < NOW() - INTERVAL '1 day');
