CREATE TABLE IF NOT EXISTS sources (
    id BIGSERIAL PRIMARY KEY,

    provider TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    board_id TEXT,

    status TEXT NOT NULL DEFAULT 'active',

    last_crawled_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_job_count INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(provider, canonical_url)
);


CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,

    source_id BIGINT NOT NULL
        REFERENCES sources(id)
        ON DELETE CASCADE,

    external_job_id TEXT NOT NULL,

    provider TEXT NOT NULL,

    company TEXT,
    title TEXT NOT NULL,
    location TEXT,

    employment_type TEXT,
    workplace_type TEXT,

    posted_at TIMESTAMPTZ,
    posted_at_source TEXT,

    description_text TEXT,
    description_html TEXT,

    job_url TEXT,
    apply_url TEXT,

    raw_payload JSONB,

    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE(source_id, external_job_id)
);