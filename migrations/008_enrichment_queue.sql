CREATE TABLE IF NOT EXISTS enrichment_queue (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    priority INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reason TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_error TEXT,
    CONSTRAINT enrichment_queue_status_check
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT enrichment_queue_reason_check
        CHECK (reason IN ('new_job', 'changed_job', 'bootstrap')),
    CONSTRAINT enrichment_queue_priority_check CHECK (priority IN (1, 2, 3)),
    UNIQUE (job_id, content_hash)
);

CREATE INDEX IF NOT EXISTS enrichment_queue_claim_idx
ON enrichment_queue (status, priority, created_at);
