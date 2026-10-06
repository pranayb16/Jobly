-- Queue work is versioned and retryable without hot-looping.
ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS openrouter_interaction_id TEXT;

UPDATE job_enrichments
SET openrouter_interaction_id = gemini_interaction_id
WHERE openrouter_interaction_id IS NULL;

ALTER TABLE enrichment_queue
ADD COLUMN IF NOT EXISTS schema_version TEXT;

UPDATE enrichment_queue
SET schema_version = COALESCE(NULLIF(schema_version, ''), 'v3');

ALTER TABLE enrichment_queue
ALTER COLUMN schema_version SET DEFAULT 'v3';

ALTER TABLE enrichment_queue
ALTER COLUMN schema_version SET NOT NULL;

ALTER TABLE enrichment_queue
ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

ALTER TABLE enrichment_queue
ADD COLUMN IF NOT EXISTS error_class TEXT;

ALTER TABLE enrichment_queue
ADD COLUMN IF NOT EXISTS retryable BOOLEAN;

ALTER TABLE enrichment_queue
DROP CONSTRAINT IF EXISTS enrichment_queue_job_id_content_hash_key;

ALTER TABLE enrichment_queue
DROP CONSTRAINT IF EXISTS enrichment_queue_job_hash_schema_key;

ALTER TABLE enrichment_queue
ADD CONSTRAINT enrichment_queue_job_hash_schema_key
UNIQUE (job_id, content_hash, schema_version);

CREATE INDEX IF NOT EXISTS enrichment_queue_retry_claim_idx
ON enrichment_queue (status, schema_version, next_attempt_at, priority, created_at);

-- Repair malformed legacy JSON values before adding write-time protections.
UPDATE job_enrichments
SET
    related_roles = CASE WHEN jsonb_typeof(related_roles) = 'array' THEN related_roles ELSE '[]'::jsonb END,
    role_keywords = CASE WHEN jsonb_typeof(role_keywords) = 'array' THEN role_keywords ELSE '[]'::jsonb END,
    responsibility_tags = CASE WHEN jsonb_typeof(responsibility_tags) = 'array' THEN responsibility_tags ELSE '[]'::jsonb END,
    skills = CASE WHEN jsonb_typeof(skills) = 'array' THEN skills ELSE '[]'::jsonb END,
    required_skills = CASE WHEN jsonb_typeof(required_skills) = 'array' THEN required_skills ELSE '[]'::jsonb END,
    preferred_skills = CASE WHEN jsonb_typeof(preferred_skills) = 'array' THEN preferred_skills ELSE '[]'::jsonb END,
    soft_skills = CASE WHEN jsonb_typeof(soft_skills) = 'array' THEN soft_skills ELSE '[]'::jsonb END,
    education_fields = CASE WHEN jsonb_typeof(education_fields) = 'array' THEN education_fields ELSE '[]'::jsonb END,
    certifications = CASE WHEN jsonb_typeof(certifications) = 'array' THEN certifications ELSE '[]'::jsonb END,
    locations = CASE WHEN jsonb_typeof(locations) = 'array' THEN locations ELSE '[]'::jsonb END,
    preferred_locations = CASE WHEN jsonb_typeof(preferred_locations) = 'array' THEN preferred_locations ELSE '[]'::jsonb END;

UPDATE job_enrichments
SET skill_count = jsonb_array_length(skills);

ALTER TABLE job_enrichments
ADD CONSTRAINT job_enrichments_experience_range_check
CHECK (
    (years_experience_min IS NULL OR years_experience_min >= 0)
    AND (years_experience_max IS NULL OR years_experience_max >= 0)
    AND (
        years_experience_min IS NULL
        OR years_experience_max IS NULL
        OR years_experience_min <= years_experience_max
    )
) NOT VALID;

ALTER TABLE job_enrichments
ADD CONSTRAINT job_enrichments_confidence_check
CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1) NOT VALID;

ALTER TABLE job_enrichments
ADD CONSTRAINT job_enrichments_token_counts_check
CHECK (
    input_tokens >= 0
    AND output_tokens >= 0
    AND thought_tokens >= 0
    AND cached_tokens >= 0
    AND total_tokens >= 0
) NOT VALID;

ALTER TABLE job_enrichments
ADD CONSTRAINT job_enrichments_json_arrays_check
CHECK (
    jsonb_typeof(related_roles) = 'array'
    AND jsonb_typeof(role_keywords) = 'array'
    AND jsonb_typeof(responsibility_tags) = 'array'
    AND jsonb_typeof(skills) = 'array'
    AND jsonb_typeof(required_skills) = 'array'
    AND jsonb_typeof(preferred_skills) = 'array'
    AND jsonb_typeof(soft_skills) = 'array'
    AND jsonb_typeof(education_fields) = 'array'
    AND jsonb_typeof(certifications) = 'array'
    AND jsonb_typeof(locations) = 'array'
    AND jsonb_typeof(preferred_locations) = 'array'
) NOT VALID;

ALTER TABLE enrichment_queue
ADD CONSTRAINT enrichment_queue_attempts_nonnegative_check
CHECK (attempts >= 0) NOT VALID;

ALTER TABLE jobs
ADD CONSTRAINT jobs_ready_hash_check
CHECK (
    classification_status <> 'ready'
    OR classified_content_hash = content_hash
) NOT VALID;

-- Existing deployments already ran migration 018. Rewrite its function so
-- every company metric uses confirmed U.S. jobs only.
DO $$
DECLARE
    definition TEXT;
BEGIN
    SELECT pg_get_functiondef('refresh_company_hiring_stats(bigint)'::regprocedure)
    INTO definition;

    IF POSITION('j.is_us_job IS TRUE' IN definition) = 0 THEN
        definition := regexp_replace(
            definition,
            'LEFT JOIN jobs AS j\s+ON j\.company_id = c\.id',
            'LEFT JOIN jobs AS j ON j.company_id = c.id AND j.is_us_job IS TRUE'
        );
        EXECUTE definition;
    END IF;
END;
$$;

SELECT refresh_company_hiring_stats();

-- Pin the public canonical view to the production schema. The historical
-- view is large, so rewrite only its current-enrichment CTE in place.
DO $$
DECLARE
    definition TEXT;
BEGIN
    SELECT pg_get_viewdef('current_job_intelligence'::regclass, TRUE)
    INTO definition;

    IF POSITION('e.schema_version' IN definition) = 0 THEN
        definition := regexp_replace(
            definition,
            'ORDER BY e\.job_id',
            'WHERE e.schema_version = ''v3'' ORDER BY e.job_id'
        );
        EXECUTE 'CREATE OR REPLACE VIEW current_job_intelligence AS ' || definition;
    END IF;
END;
$$;
