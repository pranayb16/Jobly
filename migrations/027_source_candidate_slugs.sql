ALTER TABLE source_candidates
ADD COLUMN IF NOT EXISTS source_slug TEXT;


ALTER TABLE source_candidates
DROP CONSTRAINT IF EXISTS source_candidates_provider_canonical_url_key;

DROP INDEX IF EXISTS source_candidates_provider_canonical_url_key;


UPDATE source_candidates
SET
    provider = CASE LOWER(BTRIM(provider))
        WHEN 'ashbyhq' THEN 'ashby'
        ELSE LOWER(BTRIM(provider))
    END,
    canonical_url = NULLIF(BTRIM(canonical_url), ''),
    source_slug = COALESCE(
        NULLIF(BTRIM(source_slug), ''),
        NULLIF(BTRIM(board_id), ''),
        NULLIF(
            SUBSTRING(
                canonical_url
                FROM '^https?://[^/]+/([^/?#]+)'
            ),
            ''
        )
    );


ALTER TABLE source_candidates
ALTER COLUMN canonical_url DROP NOT NULL;


-- Merge any existing URL variants that identify the same provider board before
-- enforcing the new staging key. The oldest row remains the stable survivor.
WITH duplicate_groups AS (
    SELECT
        provider,
        source_slug,
        MIN(id) AS keep_id,
        (ARRAY_AGG(
            canonical_url
            ORDER BY (canonical_url IS NOT NULL) DESC, id
        ))[1] AS canonical_url,
        (ARRAY_AGG(
            board_id
            ORDER BY (NULLIF(BTRIM(board_id), '') IS NOT NULL) DESC, id
        ))[1] AS board_id,
        (ARRAY_AGG(
            company_name
            ORDER BY (NULLIF(BTRIM(company_name), '') IS NOT NULL) DESC, id
        ))[1] AS company_name,
        (ARRAY_AGG(
            status
            ORDER BY CASE status
                WHEN 'promoted' THEN 0
                WHEN 'valid' THEN 1
                WHEN 'validating' THEN 2
                WHEN 'pending' THEN 3
                ELSE 4
            END,
            id
        ))[1] AS status,
        MAX(validation_attempts) AS validation_attempts,
        MAX(last_validated_at) AS last_validated_at
    FROM source_candidates
    WHERE source_slug IS NOT NULL
    GROUP BY provider, source_slug
    HAVING COUNT(*) > 1
)
UPDATE source_candidates AS candidate
SET
    canonical_url = duplicate_groups.canonical_url,
    board_id = COALESCE(duplicate_groups.board_id, duplicate_groups.source_slug),
    company_name = duplicate_groups.company_name,
    status = duplicate_groups.status,
    validation_attempts = duplicate_groups.validation_attempts,
    last_validated_at = duplicate_groups.last_validated_at,
    updated_at = NOW()
FROM duplicate_groups
WHERE candidate.id = duplicate_groups.keep_id;


DELETE FROM source_candidates AS candidate
USING (
    SELECT provider, source_slug, MIN(id) AS keep_id
    FROM source_candidates
    WHERE source_slug IS NOT NULL
    GROUP BY provider, source_slug
    HAVING COUNT(*) > 1
) AS duplicate_groups
WHERE candidate.provider = duplicate_groups.provider
  AND candidate.source_slug = duplicate_groups.source_slug
  AND candidate.id <> duplicate_groups.keep_id;


CREATE UNIQUE INDEX IF NOT EXISTS
source_candidates_provider_slug_key
ON source_candidates (provider, source_slug)
WHERE source_slug IS NOT NULL;


CREATE UNIQUE INDEX IF NOT EXISTS
source_candidates_provider_canonical_url_key
ON source_candidates (provider, canonical_url);
