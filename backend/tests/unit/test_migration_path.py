from jobly.commands.migrate import DEFAULT_MIGRATIONS_DIR


def test_default_migration_path_contains_ordered_migrations():
    files = sorted(path.name for path in DEFAULT_MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    assert files[0] == "001_initial.sql"
    assert files[-1] == "012_source_candidates.sql"


def test_docker_image_copies_migrations_and_candidate_import_source():
    dockerfile = (DEFAULT_MIGRATIONS_DIR.parent / "backend" / "Dockerfile").read_text()
    assert "COPY migrations /app/migrations" in dockerfile
    assert "COPY data/cleaned/valid_sources.csv" in dockerfile
