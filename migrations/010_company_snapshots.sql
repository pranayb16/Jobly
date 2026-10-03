CREATE TABLE IF NOT EXISTS company_daily_snapshots (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    total_open_jobs INTEGER NOT NULL,
    new_jobs INTEGER NOT NULL DEFAULT 0,
    removed_jobs INTEGER NOT NULL DEFAULT 0,
    changed_jobs INTEGER NOT NULL DEFAULT 0,
    enriched_jobs INTEGER NOT NULL DEFAULT 0,
    enrichment_coverage REAL NOT NULL DEFAULT 0,
    role_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    skill_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    seniority_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    location_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    workplace_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    domain_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS company_snapshots_date_idx
ON company_daily_snapshots (snapshot_date DESC);
