-- ============================================================
-- Jobly pipeline observability
--
-- pipeline_stage_runs:
--     one summarized record per pipeline stage
--
-- pipeline_events:
--     important structured warnings/errors
--
-- pipeline_logs:
--     raw Python log messages for debugging
-- ============================================================


CREATE TABLE IF NOT EXISTS pipeline_stage_runs (
    id BIGSERIAL PRIMARY KEY,

    pipeline_run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(id)
        ON DELETE CASCADE,

    stage TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'running',

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    finished_at TIMESTAMPTZ,

    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,

    error TEXT,

    CONSTRAINT pipeline_stage_runs_status_check
        CHECK (
            status IN (
                'running',
                'success',
                'partial_success',
                'failed',
                'skipped'
            )
        ),

    UNIQUE (
        pipeline_run_id,
        stage
    )
);


CREATE INDEX IF NOT EXISTS
pipeline_stage_runs_pipeline_idx
ON pipeline_stage_runs (
    pipeline_run_id,
    started_at
);


CREATE TABLE IF NOT EXISTS pipeline_events (
    id BIGSERIAL PRIMARY KEY,

    pipeline_run_id BIGINT
        REFERENCES pipeline_runs(id)
        ON DELETE CASCADE,

    stage TEXT,

    severity TEXT NOT NULL,

    event_type TEXT NOT NULL,

    source_id BIGINT
        REFERENCES sources(id)
        ON DELETE SET NULL,

    job_id BIGINT
        REFERENCES jobs(id)
        ON DELETE SET NULL,

    queue_id BIGINT
        REFERENCES enrichment_queue(id)
        ON DELETE SET NULL,

    provider TEXT,

    model TEXT,

    message TEXT NOT NULL,

    details JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pipeline_events_severity_check
        CHECK (
            severity IN (
                'info',
                'warning',
                'error',
                'critical'
            )
        )
);


CREATE INDEX IF NOT EXISTS
pipeline_events_pipeline_idx
ON pipeline_events (
    pipeline_run_id,
    created_at
);


CREATE INDEX IF NOT EXISTS
pipeline_events_severity_idx
ON pipeline_events (
    pipeline_run_id,
    severity,
    created_at
);


CREATE TABLE IF NOT EXISTS pipeline_logs (
    id BIGSERIAL PRIMARY KEY,

    pipeline_run_id BIGINT
        REFERENCES pipeline_runs(id)
        ON DELETE CASCADE,

    stage TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    level TEXT NOT NULL,

    logger TEXT NOT NULL,

    message TEXT NOT NULL,

    exception TEXT
);


CREATE INDEX IF NOT EXISTS
pipeline_logs_pipeline_idx
ON pipeline_logs (
    pipeline_run_id,
    created_at
);


CREATE INDEX IF NOT EXISTS
pipeline_logs_level_idx
ON pipeline_logs (
    pipeline_run_id,
    level,
    created_at
);