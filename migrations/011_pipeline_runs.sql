CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    source_target INTEGER,
    sources_attempted INTEGER,
    sources_successful INTEGER,
    sources_failed INTEGER,
    jobs_seen INTEGER,
    jobs_new INTEGER,
    jobs_changed INTEGER,
    jobs_removed INTEGER,
    enrichments_processed INTEGER,
    enrichments_completed INTEGER,
    enrichments_failed INTEGER,
    enrichment_backlog INTEGER,
    snapshots_created INTEGER,
    error TEXT,
    CONSTRAINT pipeline_runs_status_check
        CHECK (status IN ('running', 'success', 'partial_success', 'failed'))
);

ALTER TABLE crawl_runs
ADD COLUMN IF NOT EXISTS pipeline_run_id BIGINT REFERENCES pipeline_runs(id) ON DELETE SET NULL;

ALTER TABLE job_events
ADD COLUMN IF NOT EXISTS pipeline_run_id BIGINT REFERENCES pipeline_runs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS crawl_runs_pipeline_idx ON crawl_runs (pipeline_run_id);
CREATE INDEX IF NOT EXISTS job_events_pipeline_idx ON job_events (pipeline_run_id);
