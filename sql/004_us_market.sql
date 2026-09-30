-- ============================================================
-- Jobly U.S.-only market scope
-- ============================================================


ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS is_us_job BOOLEAN;


ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS us_location_reason TEXT;


CREATE INDEX IF NOT EXISTS jobs_us_fresh_idx
ON jobs (posted_at DESC)
WHERE
    active = TRUE
    AND is_us_job = TRUE;


-- ============================================================
-- Public publication gate
--
-- Only:
-- - active
-- - U.S. eligible
-- - AI ready
-- - AI matches current content
-- - posted within 48 hours
-- ============================================================

CREATE OR REPLACE VIEW public_jobs AS

SELECT *
FROM jobs

WHERE
    active = TRUE

    AND is_us_job = TRUE

    AND classification_status = 'ready'

    AND content_hash IS NOT NULL

    AND classified_content_hash = content_hash

    AND posted_at IS NOT NULL

    AND posted_at >=
        NOW() - INTERVAL '48 hours';