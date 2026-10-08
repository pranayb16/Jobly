from __future__ import annotations

import pytest

from jobly.sources.manager import (
    SUPPORTED_PROVIDERS,
    _next_candidate,
    _promote_candidate,
    extract_board_id,
)


class NextCandidateCursor:
    def __init__(self, candidate=None):
        self.candidate = candidate
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((" ".join(statement.split()), params))

    def fetchone(self):
        return self.candidate


def test_next_candidate_filters_to_supported_providers_and_usable_urls():
    candidate = (1, "greenhouse", "https://job-boards.greenhouse.io/example", "example", None, "pending")
    cursor = NextCandidateCursor(candidate)

    assert _next_candidate(cursor) == candidate

    sql, params = cursor.statements[1]
    assert "provider = ANY(%s::text[])" in sql
    assert set(params[0]) == SUPPORTED_PROVIDERS
    assert "canonical_url IS NOT NULL" in sql
    assert "BTRIM(canonical_url) <> ''" in sql


@pytest.mark.parametrize("provider", ["workday", "rippling", "gem", "smartrecruiters"])
def test_unsupported_provider_is_left_pending_without_database_writes(provider):
    class NoWriteConnection:
        def cursor(self):
            pytest.fail("unsupported provider must not be updated or promoted")

        def commit(self):
            pytest.fail("unsupported provider must remain untouched")

    candidate = (7, provider, "https://example.test/jobs", "slug", "Example", "pending")

    assert _promote_candidate(NoWriteConnection(), candidate, validate=True) == (False, False)


class PromoteCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, params=None):
        normalized = " ".join(statement.split())
        self.connection.statements.append((normalized, params))
        if "SELECT status FROM sources" in normalized:
            status = self.connection.existing_status
            self.connection.next_row = (status,) if status is not None else None
        elif "INSERT INTO sources" in normalized:
            self.connection.next_row = (91,)
        else:
            self.connection.next_row = None

    def fetchone(self):
        row = self.connection.next_row
        self.connection.next_row = None
        return row


class PromoteConnection:
    def __init__(self, existing_status=None):
        self.statements = []
        self.next_row = None
        self.commits = 0
        self.existing_status = existing_status

    def cursor(self):
        return PromoteCursor(self)

    def commit(self):
        self.commits += 1


def test_supported_valid_candidate_still_promotes(monkeypatch):
    monkeypatch.setattr("jobly.sources.manager.ensure_company", lambda *_args: 42)
    connection = PromoteConnection()
    candidate = (
        7,
        "lever",
        "https://jobs.lever.co/jobgether",
        "jobgether",
        "Jobgether",
        "valid",
    )

    assert _promote_candidate(connection, candidate, validate=False) == (True, False)

    statements = " ".join(statement for statement, _params in connection.statements)
    assert "INSERT INTO sources" in statements
    assert "ON CONFLICT (provider, source_slug)" in statements
    assert "status = 'active'" in statements
    assert "SET status = 'promoted'" in statements
    assert connection.commits == 1


@pytest.mark.parametrize(
    ("existing_status", "counts_as_promotion"),
    [("active", False), ("inactive", True), ("not_verified", True)],
)
def test_promotion_only_counts_an_active_status_transition(
    monkeypatch,
    existing_status,
    counts_as_promotion,
):
    monkeypatch.setattr("jobly.sources.manager.ensure_company", lambda *_args: 42)
    connection = PromoteConnection(existing_status=existing_status)
    candidate = (
        7,
        "lever",
        "https://jobs.lever.co/jobgether",
        "jobgether",
        "Jobgether",
        "valid",
    )

    assert _promote_candidate(connection, candidate, validate=False) == (
        counts_as_promotion,
        False,
    )


@pytest.mark.parametrize(
    ("provider", "url", "expected"),
    [
        ("greenhouse", "https://job-boards.greenhouse.io/databricks", "databricks"),
        ("ashby", "https://jobs.ashbyhq.com/plaid", "plaid"),
        ("lever", "https://jobs.lever.co/jobgether", "jobgether"),
    ],
)
def test_extract_board_id_for_supported_providers(provider, url, expected):
    assert extract_board_id(url, provider) == expected
