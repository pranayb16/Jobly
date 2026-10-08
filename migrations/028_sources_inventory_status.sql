ALTER TABLE sources
ADD COLUMN IF NOT EXISTS source_slug TEXT;


UPDATE sources
SET source_slug = COALESCE(
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


ALTER TABLE sources
ALTER COLUMN canonical_url DROP NOT NULL;


CREATE UNIQUE INDEX IF NOT EXISTS
sources_provider_slug_key
ON sources (provider, source_slug)
WHERE source_slug IS NOT NULL;


CREATE INDEX IF NOT EXISTS
sources_status_idx
ON sources (status, id);
