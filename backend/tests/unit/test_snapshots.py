from jobly.intelligence.snapshots import (
    calculate_ai_counts,
    calculate_coverage,
)


def test_enrichment_coverage_is_calculated():
    assert calculate_coverage(
        3,
        4,
    ) == 0.75


def test_snapshot_coverage_handles_zero_enriched_jobs():
    assert calculate_coverage(
        0,
        10,
    ) == 0.0

    assert calculate_ai_counts(
        []
    ) == {
        "role_counts": {},
        "skill_counts": {},
        "seniority_counts": {},
        "location_counts": {},
        "workplace_counts": {},
        "domain_counts": {},
    }


def test_snapshot_uses_canonical_skills_and_locations():
    data = [
        {
            "standardized_title":
                "Backend Software Engineer",

            "job_family":
                "software_engineering",

            "skills": [
                "Python",
                "PostgreSQL",
            ],

            "seniority":
                "senior",

            "locations": [
                {
                    "city":
                        "Chicago",

                    "state":
                        "Illinois",

                    "state_code":
                        "IL",

                    "country":
                        "United States",

                    "country_code":
                        "US",
                }
            ],

            "workplace_type":
                "hybrid",

            "domain_tags": [
                "developer_tools"
            ],
        }
    ]

    counts = calculate_ai_counts(
        data
    )

    assert counts[
        "role_counts"
    ] == {
        "Backend Software Engineer": 1
    }

    assert counts[
        "skill_counts"
    ] == {
        "Python": 1,
        "PostgreSQL": 1,
    }

    assert counts[
        "seniority_counts"
    ] == {
        "senior": 1
    }

    assert counts[
        "location_counts"
    ] == {
        "Chicago, Illinois, United States": 1
    }

    assert counts[
        "workplace_counts"
    ] == {
        "hybrid": 1
    }


def test_snapshot_migration_and_upsert_are_idempotent():
    migration = open(
        "../migrations/010_company_snapshots.sql",
        encoding="utf-8",
    ).read()

    source = open(
        "jobly/intelligence/snapshots.py",
        encoding="utf-8",
    ).read()

    assert (
        "UNIQUE (company_id, snapshot_date)"
        in migration
    )

    normalized_source = " ".join(
        source.split()
    )

    assert (
        "ON CONFLICT"
        in normalized_source
    )

    assert (
        "company_id"
        in normalized_source
    )

    assert (
        "snapshot_date"
        in normalized_source
    )

    assert (
        "DO UPDATE SET"
        in normalized_source
    )