CREATE TABLE IF NOT EXISTS job_versions (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    title TEXT,
    location TEXT,
    employment_type TEXT,
    workplace_type TEXT,
    description_text TEXT,
    description_html TEXT,
    raw_payload JSONB,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS job_versions_job_captured_idx
ON job_versions (job_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS job_events (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    crawl_run_id BIGINT REFERENCES crawl_runs(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT job_events_type_check
        CHECK (event_type IN ('created', 'changed', 'removed', 'reactivated'))
);

CREATE INDEX IF NOT EXISTS job_events_job_occurred_idx
ON job_events (job_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS job_events_type_occurred_idx
ON job_events (event_type, occurred_at DESC);
