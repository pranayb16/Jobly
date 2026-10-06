import logging

from jobly.crawling.repository import (
    CRAWL_SOURCE_LOCK_NAMESPACE,
    acquire_source_lock,
    release_source_lock,
)
from jobly.observability.db_log_handler import PipelineDatabaseLogHandler


class Cursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.conn.statements.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.conn.result


class Connection:
    def __init__(self, result=(True,)):
        self.result = result
        self.statements = []

    def cursor(self, **_kwargs):
        return Cursor(self)


def test_crawl_source_lock_is_session_scoped_and_released():
    conn = Connection()
    assert acquire_source_lock(conn, 42) is True
    release_source_lock(conn, 42)
    assert conn.statements == [
        ("SELECT pg_try_advisory_lock(%s, %s)", (CRAWL_SOURCE_LOCK_NAMESPACE, 42)),
        ("SELECT pg_advisory_unlock(%s, %s)", (CRAWL_SOURCE_LOCK_NAMESPACE, 42)),
    ]


def test_frontend_date_salary_and_query_contracts_do_not_fabricate_data():
    jobs_route = open("../frontend/app/api/jobs/route.ts", encoding="utf-8").read()
    detail_route = open("../frontend/app/api/jobs/[id]/route.ts", encoding="utf-8").read()
    jobs_page = open("../frontend/components/JobsPage.tsx", encoding="utf-8").read()
    detail = open("../frontend/components/jobs/JobDetail.tsx", encoding="utf-8").read()

    scope = jobs_route[jobs_route.index("function isWithinLast48Hours"):jobs_route.index("async function fetchRecentJobs")]
    assert "first_seen_at" not in scope
    assert "posted_since=" in jobs_route
    assert "setInterval" not in jobs_page
    assert "salary_min" in detail_route and "salary_period" in detail_route
    assert "First observed" in detail
    assert "Up to" in detail


def test_source_candidate_recovery_and_dependency_hardening_are_present():
    manager = open("jobly/sources/manager.py", encoding="utf-8").read()
    pyproject = open("pyproject.toml", encoding="utf-8").read()
    compose = open("../infra/observability/docker-compose.yml", encoding="utf-8").read()
    assert "recovered stale validation lease" in manager
    assert '"pending" if transient else "invalid"' in manager
    assert "google-genai" not in pyproject
    assert ":latest" not in compose
    assert "GRAFANA_ADMIN_PASSWORD:?" in compose


def test_pipeline_log_handler_reuses_one_connection(monkeypatch):
    class LogCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args):
            pass

    class LogConnection:
        closed = False

        def cursor(self):
            return LogCursor()

        def commit(self):
            pass

        def close(self):
            self.closed = True

    calls = []
    monkeypatch.setattr("jobly.observability.db_log_handler.get_pipeline_run_id", lambda: 1)
    monkeypatch.setattr("jobly.observability.db_log_handler.get_connection", lambda: calls.append(1) or LogConnection())
    handler = PipelineDatabaseLogHandler()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    handler.emit(record)
    handler.emit(record)
    assert len(calls) == 1
    handler.close()
