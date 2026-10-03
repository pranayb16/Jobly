-- ============================================================
-- Gemini per-job token usage
-- ============================================================

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS gemini_interaction_id TEXT;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS input_tokens BIGINT
NOT NULL DEFAULT 0;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS output_tokens BIGINT
NOT NULL DEFAULT 0;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS thought_tokens BIGINT
NOT NULL DEFAULT 0;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS cached_tokens BIGINT
NOT NULL DEFAULT 0;

ALTER TABLE job_enrichments
ADD COLUMN IF NOT EXISTS total_tokens BIGINT
NOT NULL DEFAULT 0;


CREATE INDEX IF NOT EXISTS
job_enrichments_created_at_idx
ON job_enrichments (created_at DESC);