-- ============================================================
-- Remove legacy 48-hour publication window.
--
-- Jobly now tracks the full current hiring inventory rather
-- than only very recently posted jobs.
-- ============================================================


CREATE OR REPLACE VIEW public_jobs AS

SELECT *
FROM jobs

WHERE
    active = TRUE

    AND is_us_job = TRUE

    AND classification_status = 'ready'

    AND content_hash IS NOT NULL

    AND classified_content_hash = content_hash;