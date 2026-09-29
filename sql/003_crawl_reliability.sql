-- ============================================================
-- Jobly crawl reliability migration
-- ============================================================


-- ------------------------------------------------------------
-- Source health
-- ------------------------------------------------------------

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ;

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS last_failure_at TIMESTAMPTZ;

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE sources
ADD COLUMN IF NOT EXISTS last_error TEXT;


-- ------------------------------------------------------------
-- Crawl history
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS crawl_runs (
    id BIGSERIAL PRIMARY KEY,

    source_id BIGINT NOT NULL
        REFERENCES sources(id)
        ON DELETE CASCADE,

    started_at TIMESTAMPTZ
        NOT NULL DEFAULT NOW(),

    finished_at TIMESTAMPTZ,

    status TEXT NOT NULL
        DEFAULT 'running',

    job_count INTEGER,

    error TEXT,

    CHECK (
        status IN (
            'running',
            'success',
            'failed'
        )
    )
);


-- ------------------------------------------------------------
-- Job crawl state
-- ------------------------------------------------------------

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS
last_seen_crawl_id BIGINT
REFERENCES crawl_runs(id)
ON DELETE SET NULL;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS
removed_at TIMESTAMPTZ;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS
observed_new_after TIMESTAMPTZ;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS
observed_new_before TIMESTAMPTZ;


-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS
crawl_runs_source_started_idx
ON crawl_runs (
    source_id,
    started_at DESC
);

CREATE INDEX IF NOT EXISTS
jobs_source_active_idx
ON jobs (
    source_id,
    active
);

CREATE INDEX IF NOT EXISTS
jobs_last_seen_crawl_idx
ON jobs (
    last_seen_crawl_id
);