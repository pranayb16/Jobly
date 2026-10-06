from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from jobly.api.main import app
from jobly.api.routes.admin_runs import (
    require_admin_access,
    router as admin_runs_router,
)
from jobly.config import get_settings
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


def test_admin_routes_reject_unauthenticated_requests(
    monkeypatch,
):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    get_settings.cache_clear()

    protected_app = FastAPI()
    protected_app.include_router(admin_runs_router)
    client = TestClient(protected_app)

    response = client.get("/api/admin/runs")
    wrong = client.get(
        "/api/admin/runs",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401

    get_settings.cache_clear()


def test_admin_routes_fail_closed_without_configured_token(
    monkeypatch,
):
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()

    protected_app = FastAPI()
    protected_app.include_router(admin_runs_router)
    response = TestClient(protected_app).get("/api/admin/runs")

    assert response.status_code == 401

    get_settings.cache_clear()


def test_admin_dependency_accepts_matching_bearer_token(
    monkeypatch,
):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    get_settings.cache_clear()

    require_admin_access(
        HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test-admin-token",
        )
    )

    get_settings.cache_clear()
