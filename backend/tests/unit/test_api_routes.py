from jobly.api.main import app


def test_jobs_and_intelligence_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/jobs" in paths
    assert "/api/jobs/{job_id}" in paths
    assert "/api/companies" in paths
    assert "/api/companies/{slug}/trends" in paths
    assert "/api/trends" in paths
    assert "/api/roles/{role}" in paths
    assert "/api/skills/{skill}" in paths
