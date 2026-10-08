from jobly.commands.migrate import (
    DEFAULT_MIGRATIONS_DIR,
    migration_checksum,
)


def test_default_migration_path_contains_ordered_migrations():
    files = sorted(
        path.name
        for path
        in DEFAULT_MIGRATIONS_DIR.glob(
            "[0-9][0-9][0-9]_*.sql"
        )
    )

    assert files

    assert files[0] == (
        "001_initial.sql"
    )

    numbers = [
        int(filename[:3])
        for filename
        in files
    ]

    assert numbers == sorted(
        numbers
    )

    assert len(numbers) == len(
        set(numbers)
    )


def test_default_migration_directory_exists():
    assert (
        DEFAULT_MIGRATIONS_DIR.exists()
    )

    assert (
        DEFAULT_MIGRATIONS_DIR.is_dir()
    )


def test_gcp_pipeline_uses_openrouter_v3_configuration():
    deployment = open(
        "../infra/gcp/README.md",
        encoding="utf-8",
    ).read()

    assert "OPENROUTER_API_KEY=jobly-openrouter-api-key:latest" in deployment
    assert "OPENROUTER_FREE_MODEL=openai/gpt-oss-20b:free" in deployment
    assert "OPENROUTER_PAID_MODEL=openai/gpt-oss-20b" in deployment
    assert "AI_CLASSIFICATION_VERSION=v3" in deployment
    assert "AI_PROMPT_VERSION=v3" in deployment
    assert "GEMINI_API_KEY" not in deployment
    assert "AI_MODEL=gemini" not in deployment


def test_documented_admin_api_deployment_sets_auth_secret():
    deployment = open(
        "../infra/gcp/README.md",
        encoding="utf-8",
    ).read()

    assert "ADMIN_API_TOKEN=jobly-admin-api-token:latest" in deployment


def test_migrations_have_integrity_checksums_and_queue_schema_versions(tmp_path):
    migration = tmp_path / "001_test.sql"
    migration.write_text("SELECT 1;", encoding="utf-8")
    first = migration_checksum(migration)
    migration.write_text("SELECT 2;", encoding="utf-8")
    assert migration_checksum(migration) != first

    reliability = open("../migrations/023_integrity_and_reliability.sql", encoding="utf-8").read()
    normalized = " ".join(reliability.split())
    assert "schema_version TEXT" in reliability
    assert "UNIQUE (job_id, content_hash, schema_version)" in reliability
    assert "job_enrichments_experience_range_check" in normalized
    assert "job_enrichments_confidence_check" in normalized


def test_one_day_enrichment_migration_updates_jobs_and_queue():
    migration = open(
        "../migrations/025_enrichment_window_1_day.sql",
        encoding="utf-8",
    ).read()
    normalized = " ".join(migration.split())

    assert normalized.count("INTERVAL '1 day'") == 2
    assert "older_than_1_day" in migration
    assert "missing_posted_at" in migration
    assert "UPDATE enrichment_queue AS q" in normalized


def test_one_day_cleanup_migration_expires_stale_queue_versions():
    migration = open(
        "../migrations/026_expire_out_of_window_enrichment.sql",
        encoding="utf-8",
    ).read()
    normalized = " ".join(migration.split())

    assert normalized.count("INTERVAL '1 day'") == 2
    assert "q.content_hash" not in normalized
    assert "q.status IN ('pending', 'processing')" in normalized


def test_source_candidate_slug_migration_backfills_deduplicates_and_indexes():
    migration = open(
        "../migrations/027_source_candidate_slugs.sql",
        encoding="utf-8",
    ).read()
    normalized = " ".join(migration.split())

    assert "ADD COLUMN IF NOT EXISTS source_slug TEXT" in normalized
    assert "ALTER COLUMN canonical_url DROP NOT NULL" in normalized
    assert "BTRIM(board_id)" in normalized
    assert "WHEN 'ashbyhq' THEN 'ashby'" in normalized
    assert "SUBSTRING" in normalized
    assert "DELETE FROM source_candidates AS candidate" in normalized
    assert "ON source_candidates (provider, source_slug)" in normalized
    assert "WHERE source_slug IS NOT NULL" in normalized
    assert "ON source_candidates (provider, canonical_url)" in normalized


def test_sources_inventory_migration_adds_slug_and_status_lookup():
    migration = open(
        "../migrations/028_sources_inventory_status.sql",
        encoding="utf-8",
    ).read()
    normalized = " ".join(migration.split())

    assert "ADD COLUMN IF NOT EXISTS source_slug TEXT" in normalized
    assert "ALTER COLUMN canonical_url DROP NOT NULL" in normalized
    assert "BTRIM(board_id)" in normalized
    assert "ON sources (provider, source_slug)" in normalized
    assert "WHERE source_slug IS NOT NULL" in normalized
    assert "ON sources (status, id)" in normalized
