from jobly.api.main import app
from jobly.products.jobs.routes import _normalize_canonical_row


def test_jobs_and_intelligence_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/jobs" in paths
    assert "/api/jobs/{job_id}" in paths
    assert "/api/companies" in paths
    assert "/api/companies/{slug}" in paths
    assert "/api/companies/{slug}/trends" in paths
    assert "/api/admin/runs" in paths
    assert "/api/admin/runs/{run_id}" in paths
    assert "/api/admin/runs/{run_id}/logs" in paths
    assert "/api/trends" in paths
    assert "/api/roles/{role}" in paths
    assert "/api/skills/{skill}" in paths


def test_jobs_response_normalizes_legacy_json_collections():
    row = _normalize_canonical_row(
        {
            "related_roles": {},
            "skills": {"Python": "required"},
            "locations": None,
            "ai_locations": {},
        }
    )

    assert row["related_roles"] == []
    assert row["skills"] == ["Python"]
    assert row["locations"] == []
    assert row["ai_locations"] == []
