CREATE TABLE IF NOT EXISTS source_candidates (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    board_id TEXT,
    company_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    validation_attempts INTEGER NOT NULL DEFAULT 0,
    last_validated_at TIMESTAMPTZ,
    validation_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT source_candidates_status_check
        CHECK (status IN ('pending', 'validating', 'valid', 'invalid', 'promoted')),
    UNIQUE (provider, canonical_url)
);

CREATE INDEX IF NOT EXISTS source_candidates_status_idx
ON source_candidates (status, id);
