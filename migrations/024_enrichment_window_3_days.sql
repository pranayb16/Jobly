UPDATE jobs
SET
    enrichment_eligibility = 'not_eligible',
    enrichment_eligibility_reason = 'older_than_3_days',
    classification_status = CASE
        WHEN classification_status IN ('pending', 'processing')
            THEN 'not_eligible'
        ELSE classification_status
    END,
    classification_started_at = NULL
WHERE posted_at IS NOT NULL
  AND posted_at < NOW() - INTERVAL '7 days'
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
    last_error = 'older_than_3_days'
FROM jobs AS j
WHERE q.job_id = j.id
  AND q.content_hash = j.content_hash
  AND q.status IN ('pending', 'processing')
  AND j.posted_at IS NOT NULL
  AND j.posted_at < NOW() - INTERVAL '3 days';