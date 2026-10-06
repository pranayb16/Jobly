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

            "required_skills": [
                "Python",
            ],
            "preferred_skills": ["PostgreSQL"],
            "skills": ["Python", "PostgreSQL", "Communication"],

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


def test_snapshot_publication_is_atomic_and_demand_taxonomy_is_consistent():
    source = open("jobly/intelligence/snapshots.py", encoding="utf-8").read()
    assert source.count("conn.commit()") == 1
    assert 'role = data.get("standardized_title")' in source
    assert 'data.get("required_skills")' in source
    assert 'data.get("preferred_skills")' in source


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


def test_company_intelligence_uses_only_confirmed_us_jobs():
    snapshot_source = open(
        "jobly/intelligence/snapshots.py",
        encoding="utf-8",
    ).read()
    hiring_stats_migration = open(
        "../migrations/018_hiring_stats_posted_at_only.sql",
        encoding="utf-8",
    ).read()

    assert snapshot_source.count("is_us_job IS TRUE") >= 3
    assert "AND j.is_us_job IS TRUE" in hiring_stats_migration
