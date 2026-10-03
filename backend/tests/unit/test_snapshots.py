from jobly.intelligence.snapshots import calculate_ai_counts, calculate_coverage


def test_enrichment_coverage_is_calculated():
    assert calculate_coverage(3, 4) == 0.75


def test_snapshot_coverage_handles_zero_enriched_jobs():
    assert calculate_coverage(0, 10) == 0.0
    assert calculate_ai_counts([]) == {
        "role_counts": {}, "skill_counts": {}, "seniority_counts": {},
        "location_counts": {}, "workplace_counts": {}, "domain_counts": {},
    }


def test_snapshot_migration_and_upsert_are_idempotent():
    migration = open("../migrations/010_company_snapshots.sql", encoding="utf-8").read()
    source = open("jobly/intelligence/snapshots.py", encoding="utf-8").read()
    assert "UNIQUE (company_id, snapshot_date)" in migration
    assert "ON CONFLICT (company_id, snapshot_date) DO UPDATE" in source
