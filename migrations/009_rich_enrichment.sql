CREATE TABLE IF NOT EXISTS job_enrichments (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    data JSONB NOT NULL,
    confidence REAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (job_id, content_hash, schema_version)
);

CREATE INDEX IF NOT EXISTS job_enrichments_job_idx ON job_enrichments (job_id);
CREATE INDEX IF NOT EXISTS job_enrichments_schema_idx ON job_enrichments (schema_version);
CREATE INDEX IF NOT EXISTS job_enrichments_data_gin_idx ON job_enrichments USING GIN (data);
