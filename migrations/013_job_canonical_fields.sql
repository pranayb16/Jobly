-- ============================================================
-- Jobly canonical job intelligence fields
--
-- jobs:
--     current ATS/raw facts
--
-- job_enrichments:
--     semantic/AI extracted facts
--
-- job_versions + job_events:
--     historical evidence
--
-- current_job_intelligence:
--     flattened current canonical representation
-- ============================================================


-- ============================================================
-- Promote frequently queried enrichment fields
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS standardized_title TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS job_family TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS job_subfamily TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS related_roles JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS role_track TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS seniority TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS leadership_level TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS role_keywords JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS responsibility_tags JSONB
NOT NULL DEFAULT '[]'::jsonb;


-- ============================================================
-- Skills
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS skills JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS required_skills JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS preferred_skills JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS soft_skills JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS skill_count INTEGER
NOT NULL DEFAULT 0;


-- ============================================================
-- Experience
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS years_experience_min INTEGER;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS years_experience_max INTEGER;


-- ============================================================
-- Education / certifications
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS education_required TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS education_preferred TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS education_level TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS education_fields JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS certifications JSONB
NOT NULL DEFAULT '[]'::jsonb;


-- ============================================================
-- Location
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS locations JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS preferred_locations JSONB
NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS city TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS state TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS state_code TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS country TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS country_code TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS workplace_type TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS relocation_available BOOLEAN;


-- ============================================================
-- Employment
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS employment_type TEXT;


-- ============================================================
-- Compensation
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS salary_min NUMERIC;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS salary_max NUMERIC;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS salary_currency TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS salary_period TEXT;


-- ============================================================
-- Work authorization / legal
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS visa_sponsorship TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS work_authorization_required BOOLEAN;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS citizenship_requirement TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS security_clearance_required BOOLEAN;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS security_clearance_level TEXT;


-- ============================================================
-- Backfill promoted columns from existing JSONB enrichment
-- where possible.
-- ============================================================

UPDATE job_enrichments
SET
    standardized_title = COALESCE(
        standardized_title,
        NULLIF(data->>'standardized_title', '')
    ),

    job_family = COALESCE(
        job_family,
        NULLIF(data->>'job_family', '')
    ),

    job_subfamily = COALESCE(
        job_subfamily,
        NULLIF(data->>'job_subfamily', '')
    ),

    related_roles = CASE
        WHEN related_roles = '[]'::jsonb
        THEN COALESCE(data->'related_roles', '[]'::jsonb)
        ELSE related_roles
    END,

    role_track = COALESCE(
        role_track,
        NULLIF(data->>'role_track', '')
    ),

    seniority = COALESCE(
        seniority,
        NULLIF(data->>'seniority', '')
    ),

    leadership_level = COALESCE(
        leadership_level,
        NULLIF(data->>'leadership_level', '')
    ),

    role_keywords = CASE
        WHEN role_keywords = '[]'::jsonb
        THEN COALESCE(data->'role_keywords', '[]'::jsonb)
        ELSE role_keywords
    END,

    responsibility_tags = CASE
        WHEN responsibility_tags = '[]'::jsonb
        THEN COALESCE(data->'responsibility_tags', '[]'::jsonb)
        ELSE responsibility_tags
    END,

    required_skills = CASE
        WHEN required_skills = '[]'::jsonb
        THEN COALESCE(data->'required_skills', '[]'::jsonb)
        ELSE required_skills
    END,

    preferred_skills = CASE
        WHEN preferred_skills = '[]'::jsonb
        THEN COALESCE(data->'preferred_skills', '[]'::jsonb)
        ELSE preferred_skills
    END,

    soft_skills = CASE
        WHEN soft_skills = '[]'::jsonb
        THEN COALESCE(data->'soft_skills', '[]'::jsonb)
        ELSE soft_skills
    END,

    skills = CASE
        WHEN skills = '[]'::jsonb
        THEN
            COALESCE(data->'required_skills', '[]'::jsonb)
            ||
            COALESCE(data->'preferred_skills', '[]'::jsonb)
            ||
            COALESCE(data->'soft_skills', '[]'::jsonb)
        ELSE skills
    END,

    years_experience_min = COALESCE(
        years_experience_min,
        CASE
            WHEN data->>'years_experience_min' ~ '^\d+$'
            THEN (data->>'years_experience_min')::integer
        END
    ),

    years_experience_max = COALESCE(
        years_experience_max,
        CASE
            WHEN data->>'years_experience_max' ~ '^\d+$'
            THEN (data->>'years_experience_max')::integer
        END
    ),

    education_required = COALESCE(
        education_required,
        NULLIF(data->>'education_required', '')
    ),

    education_preferred = COALESCE(
        education_preferred,
        NULLIF(data->>'education_preferred', '')
    ),

    education_level = COALESCE(
        education_level,
        NULLIF(data->>'education_level', '')
    ),

    education_fields = CASE
        WHEN education_fields = '[]'::jsonb
        THEN COALESCE(data->'education_fields', '[]'::jsonb)
        ELSE education_fields
    END,

    certifications = CASE
        WHEN certifications = '[]'::jsonb
        THEN
            COALESCE(data->'required_certifications', '[]'::jsonb)
            ||
            COALESCE(data->'preferred_certifications', '[]'::jsonb)
        ELSE certifications
    END,

    locations = CASE
        WHEN locations = '[]'::jsonb
        THEN COALESCE(data->'locations', '[]'::jsonb)
        ELSE locations
    END,

    preferred_locations = CASE
        WHEN preferred_locations = '[]'::jsonb
        THEN COALESCE(data->'preferred_locations', '[]'::jsonb)
        ELSE preferred_locations
    END,

    city = COALESCE(
        city,
        NULLIF(data->'locations'->0->>'city', '')
    ),

    state = COALESCE(
        state,
        NULLIF(data->'locations'->0->>'state', ''),
        NULLIF(data->'locations'->0->>'region', '')
    ),

    state_code = COALESCE(
        state_code,
        NULLIF(data->'locations'->0->>'state_code', '')
    ),

    country = COALESCE(
        country,
        NULLIF(data->'locations'->0->>'country', '')
    ),

    country_code = COALESCE(
        country_code,
        NULLIF(data->'locations'->0->>'country_code', '')
    ),

    workplace_type = COALESCE(
        workplace_type,
        NULLIF(data->>'workplace_type', '')
    ),

    relocation_available = COALESCE(
        relocation_available,
        CASE
            WHEN LOWER(data->>'relocation_available') IN ('true', 'false')
            THEN (data->>'relocation_available')::boolean
        END
    ),

    employment_type = COALESCE(
        employment_type,
        NULLIF(data->>'employment_type', '')
    ),

    salary_min = COALESCE(
        salary_min,
        CASE
            WHEN data->>'salary_min' ~ '^\d+(\.\d+)?$'
            THEN (data->>'salary_min')::numeric
        END
    ),

    salary_max = COALESCE(
        salary_max,
        CASE
            WHEN data->>'salary_max' ~ '^\d+(\.\d+)?$'
            THEN (data->>'salary_max')::numeric
        END
    ),

    salary_currency = COALESCE(
        salary_currency,
        NULLIF(data->>'salary_currency', '')
    ),

    salary_period = COALESCE(
        salary_period,
        NULLIF(data->>'salary_period', '')
    ),

    visa_sponsorship = COALESCE(
        visa_sponsorship,
        NULLIF(data->>'visa_sponsorship', '')
    ),

    work_authorization_required = COALESCE(
        work_authorization_required,
        CASE
            WHEN LOWER(data->>'work_authorization_required') IN ('true', 'false')
            THEN (data->>'work_authorization_required')::boolean
        END
    ),

    citizenship_requirement = COALESCE(
        citizenship_requirement,
        NULLIF(data->>'citizenship_requirement', '')
    ),

    security_clearance_required = COALESCE(
        security_clearance_required,
        CASE
            WHEN LOWER(data->>'security_clearance_required') IN ('true', 'false')
            THEN (data->>'security_clearance_required')::boolean
        END
    ),

    security_clearance_level = COALESCE(
        security_clearance_level,
        NULLIF(data->>'security_clearance_level', '')
    );


-- Recalculate skill_count after backfill.

UPDATE job_enrichments
SET skill_count = jsonb_array_length(
    CASE
        WHEN jsonb_typeof(skills) = 'array' THEN skills
        ELSE '[]'::jsonb
    END
);


-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS job_enrichments_standardized_title_idx
ON job_enrichments (standardized_title);

CREATE INDEX IF NOT EXISTS job_enrichments_family_idx
ON job_enrichments (job_family);

CREATE INDEX IF NOT EXISTS job_enrichments_subfamily_idx
ON job_enrichments (job_subfamily);

CREATE INDEX IF NOT EXISTS job_enrichments_seniority_idx
ON job_enrichments (seniority);

CREATE INDEX IF NOT EXISTS job_enrichments_role_track_idx
ON job_enrichments (role_track);

CREATE INDEX IF NOT EXISTS job_enrichments_state_idx
ON job_enrichments (state_code);

CREATE INDEX IF NOT EXISTS job_enrichments_country_idx
ON job_enrichments (country_code);

CREATE INDEX IF NOT EXISTS job_enrichments_workplace_idx
ON job_enrichments (workplace_type);

CREATE INDEX IF NOT EXISTS job_enrichments_skills_gin_idx
ON job_enrichments USING GIN (skills);

CREATE INDEX IF NOT EXISTS job_enrichments_role_keywords_gin_idx
ON job_enrichments USING GIN (role_keywords);


-- ============================================================
-- Canonical flattened view
-- ============================================================

CREATE OR REPLACE VIEW current_job_intelligence AS

WITH current_enrichment AS (
    SELECT DISTINCT ON (e.job_id)
        e.*
    FROM job_enrichments AS e
    JOIN jobs AS j
      ON j.id = e.job_id
     AND j.content_hash = e.content_hash
    WHERE e.schema_version = 'v3'
    ORDER BY
        e.job_id,
        e.created_at DESC,
        e.id DESC
),

version_stats AS (
    SELECT
        job_id,
        COUNT(*) AS old_version_count
    FROM job_versions
    GROUP BY job_id
),

change_stats AS (
    SELECT
        job_id,
        MAX(occurred_at)
            FILTER (
                WHERE event_type = 'changed'
            ) AS last_changed_at
    FROM job_events
    GROUP BY job_id
)

SELECT
    -- Identity
    j.id AS job_id,
    j.external_job_id,
    j.source_id,
    j.company_id,
    j.provider,

    j.company AS company_name,
    j.title AS original_title,
    e.standardized_title,

    j.job_url,
    j.apply_url,

    -- Timing
    j.posted_at,
    j.posted_at_source,
    j.first_seen_at,
    j.last_seen_at,
    j.removed_at,
    j.active,
    j.observed_new_after,
    j.observed_new_before,

    ROUND(
        GREATEST(
            0,
            EXTRACT(
                EPOCH FROM (
                    NOW()
                    -
                    COALESCE(
                        j.posted_at,
                        j.first_seen_at
                    )
                )
            ) / 3600.0
        ),
        2
    ) AS freshness_hours,

    CASE
        WHEN j.posted_at IS NOT NULL
        THEN COALESCE(
            j.posted_at_source,
            'posted_at'
        )
        ELSE 'first_seen_at'
    END AS freshness_source,

    j.last_seen_at AS last_verified_at,

    CASE
        WHEN NOW() - COALESCE(j.posted_at, j.first_seen_at)
            < INTERVAL '24 hours'
        THEN 'under_24h'

        WHEN NOW() - COALESCE(j.posted_at, j.first_seen_at)
            < INTERVAL '4 days'
        THEN '1_3_days'

        WHEN NOW() - COALESCE(j.posted_at, j.first_seen_at)
            < INTERVAL '8 days'
        THEN '4_7_days'

        WHEN NOW() - COALESCE(j.posted_at, j.first_seen_at)
            < INTERVAL '31 days'
        THEN '8_30_days'

        ELSE '30_plus_days'
    END AS job_age_bucket,

    -- Role
    e.job_family,
    e.job_subfamily,
    e.related_roles,
    e.role_track,
    e.seniority,
    e.leadership_level,
    e.role_keywords,
    e.responsibility_tags,

    -- Skills
    e.skills,
    e.required_skills,
    e.preferred_skills,
    e.soft_skills,
    COALESCE(e.skill_count, 0) AS skill_count,

    -- Experience
    e.years_experience_min,
    e.years_experience_max,

    -- Education
    e.education_required,
    e.education_preferred,
    e.education_level,
    e.education_fields,
    e.certifications,

    -- Location
    j.location,
    e.locations,
    e.preferred_locations,

    e.city,
    e.state,
    e.state_code,
    e.country,
    e.country_code,

    COALESCE(
        e.workplace_type,
        j.workplace_type
    ) AS workplace_type,

    e.relocation_available,

    -- Employment
    COALESCE(
        e.employment_type,
        j.employment_type
    ) AS employment_type,

    -- Compensation
    e.salary_min,
    e.salary_max,
    e.salary_currency,
    e.salary_period,

    -- Authorization / legal
    e.visa_sponsorship,
    e.work_authorization_required,
    e.citizenship_requirement,
    e.security_clearance_required,
    e.security_clearance_level,

    -- AI metadata
    e.confidence AS classification_confidence,

    -- Historical intelligence
    COALESCE(v.old_version_count, 0) + 1
        AS version_count,

    c.last_changed_at,

    EXISTS (
        SELECT 1
        FROM job_versions AS old
        WHERE old.job_id = j.id
          AND old.title IS DISTINCT FROM j.title
    ) AS title_changed,

    EXISTS (
        SELECT 1
        FROM job_versions AS old
        WHERE old.job_id = j.id
          AND old.location IS DISTINCT FROM j.location
    ) AS location_changed,

    CASE
        WHEN e.id IS NULL
        THEN NULL

        ELSE EXISTS (
            SELECT 1
            FROM job_enrichments AS old_e
            WHERE old_e.job_id = j.id
              AND old_e.content_hash <> j.content_hash
              AND (
                    old_e.salary_min
                        IS DISTINCT FROM e.salary_min

                    OR

                    old_e.salary_max
                        IS DISTINCT FROM e.salary_max
              )
        )
    END AS salary_changed,

    GREATEST(
        0,
        FLOOR(
            EXTRACT(
                EPOCH FROM (
                    COALESCE(
                        j.removed_at,
                        NOW()
                    )
                    -
                    j.first_seen_at
                )
            ) / 86400
        )::INTEGER
    ) AS days_active,

    -- Useful raw content for job detail APIs
    j.description_text,
    j.description_html

FROM jobs AS j

LEFT JOIN current_enrichment AS e
    ON e.job_id = j.id

LEFT JOIN version_stats AS v
    ON v.job_id = j.id

LEFT JOIN change_stats AS c
    ON c.job_id = j.id;
