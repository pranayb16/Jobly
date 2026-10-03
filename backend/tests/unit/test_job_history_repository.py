from __future__ import annotations

from datetime import UTC, datetime

from jobly.jobs.models import Job, JobDescription
from jobly.jobs.repository import mark_missing_jobs_inactive, save_job


class RecordingCursor:
    def __init__(self, existing=None, inserted_id=91, rowcount=1):
        self.existing = existing
        self.inserted_id = inserted_id
        self.rowcount = rowcount
        self.statements: list[tuple[str, tuple | None]] = []
        self._next = None

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))
        if "SELECT id, content_hash" in sql:
            self._next = self.existing
        elif "INSERT INTO jobs" in sql and "RETURNING id" in sql:
            self._next = (self.inserted_id,)

    def fetchone(self):
        value = self._next
        self._next = None
        return value


def make_job(*, title="Engineer", posted_at=None):
    return Job(
        external_job_id="lever-1",
        provider="lever",
        company="Example Co",
        title=title,
        location="Chicago, IL",
        posted_at=posted_at,
        description=JobDescription(text=f"{title} description"),
        raw={"id": "lever-1"},
    )


def prepare(monkeypatch):
    monkeypatch.setattr("jobly.jobs.repository.ensure_company", lambda *_args: 7)
    monkeypatch.setattr("jobly.jobs.repository.link_source_company", lambda *_args: None)


def sql_text(cursor):
    return "\n".join(statement for statement, _params in cursor.statements)


def test_new_job_creates_event_and_high_priority_queue(monkeypatch):
    prepare(monkeypatch)
    cursor = RecordingCursor(existing=None)
    result = save_job(cursor, 1, 2, None, datetime.now(UTC), make_job())
    assert result.created is True
    assert "INSERT INTO job_events" in sql_text(cursor)
    queue = next(params for statement, params in cursor.statements if "INSERT INTO enrichment_queue" in statement)
    assert queue[2:] == (1, "new_job")


def test_changed_job_preserves_version_and_queues_changed_content(monkeypatch):
    prepare(monkeypatch)
    existing = (5, "old-hash", True, "Old", "Chicago", None, None, "old", None, {}, 7)
    cursor = RecordingCursor(existing=existing)
    result = save_job(cursor, 1, 2, None, datetime.now(UTC), make_job(title="New"))
    assert result.changed is True
    assert "INSERT INTO job_versions" in sql_text(cursor)
    event_params = [params for statement, params in cursor.statements if "INSERT INTO job_events" in statement]
    assert any(params[1] == "changed" for params in event_params)
    queue = next(params for statement, params in cursor.statements if "INSERT INTO enrichment_queue" in statement)
    assert queue[2:] == (2, "changed_job")


def test_unchanged_job_does_not_create_version_or_queue(monkeypatch):
    prepare(monkeypatch)
    job = make_job()
    from jobly.enrichment.input_builder import build_content_hash

    existing = (5, build_content_hash(job), True, job.title, job.location, None, None,
                job.description.text, None, job.raw, 7)
    cursor = RecordingCursor(existing=existing)
    result = save_job(cursor, 1, 2, None, datetime.now(UTC), job)
    assert result.changed is False
    assert "INSERT INTO job_versions" not in sql_text(cursor)
    assert "INSERT INTO enrichment_queue" not in sql_text(cursor)


def test_reactivated_job_creates_reactivation_event(monkeypatch):
    prepare(monkeypatch)
    job = make_job()
    from jobly.enrichment.input_builder import build_content_hash

    existing = (5, build_content_hash(job), False, job.title, job.location, None, None,
                job.description.text, None, job.raw, 7)
    cursor = RecordingCursor(existing=existing)
    result = save_job(cursor, 1, 2, None, datetime.now(UTC), job)
    assert result.reactivated is True
    events = [params for statement, params in cursor.statements if "INSERT INTO job_events" in statement]
    assert any(params[1] == "reactivated" for params in events)


def test_removed_jobs_are_only_selected_from_active_rows():
    cursor = RecordingCursor(rowcount=2)
    assert mark_missing_jobs_inactive(cursor, 1, 2) == 2
    statement = cursor.statements[0][0]
    assert "active = TRUE" in statement
    assert "'removed'" in statement


def test_lever_job_without_posted_at_is_queued(monkeypatch):
    prepare(monkeypatch)
    cursor = RecordingCursor(existing=None)
    save_job(cursor, 1, 2, None, datetime.now(UTC), make_job(posted_at=None))
    assert "INSERT INTO enrichment_queue" in sql_text(cursor)
