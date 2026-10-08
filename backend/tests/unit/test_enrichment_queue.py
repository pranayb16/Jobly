import pytest

from jobly.commands.bootstrap_enrichment import (
    enqueue_bootstrap,
)
from jobly.enrichment.schemas_v2 import (
    JOB_ENRICHMENT_V2_JSON_SCHEMA,
    JobEnrichmentV2,
)
from jobly.enrichment.worker import (
    _build_canonical_projection,
    claim_next_queue_item,
    count_backlog,
    process_item,
    recover_stale_queue,
    run_enrichment,
    save_success,
    save_failure,
    requeue_failed_enrichment,
)


class Cursor:
    def __init__(
        self,
        connection,
    ):
        self.connection = (
            connection
        )

        self.rowcount = (
            connection.rowcounts.pop(0)
            if connection.rowcounts
            else 0
        )

    def __enter__(
        self,
    ):
        return self

    def __exit__(
        self,
        *_args,
    ):
        return False

    def execute(
        self,
        sql,
        params=None,
    ):
        self.connection.statements.append(
            (
                " ".join(
                    sql.split()
                ),
                params,
            )
        )

    def fetchone(
        self,
    ):
        if (
            self.connection
            .fetchone_values
        ):
            return (
                self.connection
                .fetchone_values
                .pop(0)
            )

        return None


class Connection:
    def __init__(
        self,
        *,
        fetchone_values=None,
        rowcounts=None,
    ):
        self.fetchone_values = list(
            fetchone_values
            or []
        )

        self.rowcounts = list(
            rowcounts
            or []
        )

        self.statements = []

        self.commits = 0

    def cursor(
        self,
        **_kwargs,
    ):
        return Cursor(
            self
        )

    def commit(
        self,
    ):
        self.commits += 1


def test_queue_claim_orders_new_then_changed_then_bootstrap():
    conn = Connection(
        fetchone_values=[
            None
        ]
    )

    assert (
        claim_next_queue_item(
            conn
        )
        is None
    )

    assert (
        "ORDER BY q.priority ASC, q.created_at ASC"
        in conn.statements[0][0]
    )

    assert "j.active = TRUE" in conn.statements[0][0]
    assert (
        "j.enrichment_eligibility = 'eligible'"
        in conn.statements[0][0]
    )
    assert "INTERVAL '1 day'" in conn.statements[0][0]
    assert "posted_at IS NULL" not in conn.statements[0][0]


def test_backlog_only_counts_jobs_inside_enrichment_window():
    conn = Connection(fetchone_values=[(4,)])

    assert count_backlog(conn) == 4
    assert "INTERVAL '1 day'" in conn.statements[0][0]


def test_stale_recovery_expires_all_out_of_window_pending_rows():
    conn = Connection()

    recover_stale_queue(conn)

    assert conn.commits == 1
    assert len(conn.statements) == 3
    assert "UPDATE jobs" in conn.statements[0][0]
    assert "missing_posted_at" in conn.statements[0][0]
    assert "INTERVAL '1 day'" in conn.statements[0][0]
    assert "UPDATE enrichment_queue AS q" in conn.statements[1][0]
    assert "q.content_hash" not in conn.statements[1][0]
    assert "INTERVAL '1 day'" in conn.statements[1][0]


def test_failed_ai_attempt_consumes_run_limit(monkeypatch):
    class RunConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def rollback(self):
            pass

    items = [
        {"queue_id": 1, "id": 11},
        {"queue_id": 2, "id": 12},
        {"queue_id": 3, "id": 13},
    ]
    claims = 0

    def claim(_conn, _excluded):
        nonlocal claims
        claims += 1
        return items.pop(0) if items else None

    def fail_after_attempt(
        _conn,
        _item,
        on_ai_attempt=None,
    ):
        assert on_ai_attempt is not None
        on_ai_attempt()
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "jobly.enrichment.worker.get_connection",
        lambda: RunConnection(),
    )
    monkeypatch.setattr(
        "jobly.enrichment.worker.recover_stale_queue",
        lambda _conn: None,
    )
    monkeypatch.setattr(
        "jobly.enrichment.worker.claim_next_queue_item",
        claim,
    )
    monkeypatch.setattr(
        "jobly.enrichment.worker.process_item",
        fail_after_attempt,
    )
    monkeypatch.setattr(
        "jobly.enrichment.worker.save_failure",
        lambda *_args: False,
    )
    monkeypatch.setattr(
        "jobly.enrichment.worker.count_backlog",
        lambda _conn: len(items),
    )

    summary = run_enrichment(limit=1)

    assert summary.ai_calls == 1
    assert summary.processed == 1
    assert summary.failed == 1
    assert claims == 1
    assert len(items) == 2


def test_inactive_job_is_rejected_before_ai(monkeypatch):
    conn = Connection(
        fetchone_values=[
            {
                "content_hash": "current-hash",
                "active": False,
                "enrichment_eligibility": "eligible",
                "posted_at": None,
            }
        ]
    )
    item = {
        "id": 11,
        "queue_id": 1,
        "queue_hash": "current-hash",
        "content_hash": "current-hash",
    }
    monkeypatch.setattr(
        "jobly.enrichment.worker.classify_job",
        lambda *_args, **_kwargs: pytest.fail(
            "inactive job reached AI"
        ),
    )

    result, usage = process_item(conn, item)

    assert result == "not_eligible"
    assert usage is None
    statements = " ".join(sql for sql, _params in conn.statements)
    assert "status = 'not_eligible'" in statements


def test_queue_schema_prevents_duplicate_job_hash_pairs():
    migration = open(
        "../migrations/008_enrichment_queue.sql",
        encoding="utf-8",
    ).read()

    assert (
        "UNIQUE (job_id, content_hash)"
        in migration
    )

    assert (
        "CHECK (priority IN (1, 2, 3))"
        in migration
    )


def test_v2_structured_schema_requires_every_dimension():
    assert (
        set(
            JOB_ENRICHMENT_V2_JSON_SCHEMA[
                "required"
            ]
        )
        ==
        set(
            JOB_ENRICHMENT_V2_JSON_SCHEMA[
                "properties"
            ]
        )
    )


def test_v2_schema_contains_canonical_fields():
    properties = (
        JOB_ENRICHMENT_V2_JSON_SCHEMA[
            "properties"
        ]
    )

    required_fields = {
        "standardized_title",
        "job_family",
        "job_subfamily",
        "related_roles",
        "role_track",
        "seniority",
        "leadership_level",
        "role_keywords",
        "responsibility_tags",
        "required_skills",
        "preferred_skills",
        "soft_skills",
        "years_experience_min",
        "years_experience_max",
        "education_required",
        "education_preferred",
        "education_level",
        "education_fields",
        "required_certifications",
        "preferred_certifications",
        "locations",
        "preferred_locations",
        "workplace_type",
        "relocation_available",
        "employment_type",
        "salary_min",
        "salary_max",
        "visa_sponsorship",
        "work_authorization_required",
        "citizenship_requirement",
        "security_clearance_required",
        "security_clearance_level",
    }

    assert (
        required_fields
        <= set(properties)
    )


def test_bootstrap_is_idempotent_by_conflict_rule():
    first = Connection(
        rowcounts=[
            3
        ]
    )

    second = Connection(
        rowcounts=[
            0
        ]
    )

    assert (
        enqueue_bootstrap(
            first,
            "v2",
        )
        == 3
    )

    assert (
        enqueue_bootstrap(
            second,
            "v2",
        )
        == 0
    )

    normalized_sql = " ".join(
        first.statements[0][0].split()
    )

    assert (
            "ON CONFLICT ( job_id, content_hash, schema_version )"
        in normalized_sql
        or
            "ON CONFLICT (job_id, content_hash, schema_version)"
        in normalized_sql
    )

    assert (
        "DO UPDATE SET"
        in normalized_sql
    )

    assert (
        "status = 'pending'"
        in normalized_sql
    )

    assert (
        "priority = 3"
        in normalized_sql
    )

    assert (
        "reason = 'bootstrap'"
        in normalized_sql
    )

    assert (
        "'completed'"
        in normalized_sql
    )

    assert (
        "'failed'"
        in normalized_sql
    )

    assert "j.enrichment_eligibility = 'eligible'" in normalized_sql
    assert "INTERVAL '1 day'" in normalized_sql
    assert "posted_at IS NULL" not in normalized_sql


def test_retryable_failure_is_delayed_with_exponential_backoff():
    conn = Connection()
    terminal = save_failure(
        conn,
        {"queue_id": 9, "queue_attempts": 3, "id": 4, "queue_hash": "hash"},
        RuntimeError("temporary outage"),
    )
    assert terminal is False
    queue_params = conn.statements[0][1]
    assert queue_params[0] == "pending"
    assert queue_params[3] is True
    assert queue_params[5] == 120


def test_invalid_payload_failure_is_terminal_and_manual_retry_is_scoped():
    conn = Connection(rowcounts=[0, 2])
    assert save_failure(
        conn,
        {"queue_id": 9, "queue_attempts": 1, "id": 4, "queue_hash": "hash"},
        ValueError("invalid payload"),
    ) is True
    assert conn.statements[0][1][0] == "failed"
    assert conn.statements[0][1][3] is False

    assert requeue_failed_enrichment(conn) == 2
    retry_sql, retry_params = conn.statements[-1]
    assert "q.retryable IS TRUE" in retry_sql
    assert retry_params == (False,)


def test_claim_is_versioned_and_only_selects_due_retries():
    conn = Connection(fetchone_values=[None])
    claim_next_queue_item(conn)
    sql = conn.statements[0][0]
    assert "q.schema_version = %s" in sql
    assert "q.next_attempt_at <= NOW()" in sql


def test_canonical_projection_combines_skills_and_certifications():
    classification = (
        JobEnrichmentV2.model_construct(
            required_skills=[
                "Python",
                "SQL",
            ],

            preferred_skills=[
                "AWS",
                "Python",
            ],

            soft_skills=[
                "Communication",
            ],

            required_certifications=[
                "AWS SAA",
            ],

            preferred_certifications=[
                "AWS SAA",
                "PMP",
            ],

            confidence=0.9,
        )
    )

    result = (
        _build_canonical_projection(
            classification
        )
    )

    assert result["skills"] == [
        "Python",
        "SQL",
        "AWS",
        "Communication",
    ]

    assert (
        result["skill_count"]
        == 4
    )

    assert result[
        "certifications"
    ] == [
        "AWS SAA",
        "PMP",
    ]


def test_stale_enrichment_does_not_insert_result(
    monkeypatch,
):
    monkeypatch.setenv(
        "AI_CLASSIFICATION_VERSION",
        "v2",
    )

    classification = (
        JobEnrichmentV2.model_construct(
            confidence=0.8
        )
    )

    item = {
        "id":
            4,

        "queue_id":
            9,

        "queue_hash":
            "old-hash",
    }

    conn = Connection(
        fetchone_values=[
            (
                "new-hash",
            )
        ]
    )

    assert (
        save_success(
            conn,
            item,
            classification,
        )
        is False
    )

    statements = "\n".join(
        sql
        for sql, _params
        in conn.statements
    )

    assert (
        "INSERT INTO job_enrichments"
        not in statements
    )

    assert (
        "stale_content_hash"
        in statements
    )


def test_canonical_migration_contains_flattened_view():
    migration = open(
        "../migrations/013_job_canonical_fields.sql",
        encoding="utf-8",
    ).read()

    assert (
        "CREATE OR REPLACE VIEW current_job_intelligence"
        in migration
    )

    assert (
        "version_count"
        in migration
    )

    assert (
        "last_changed_at"
        in migration
    )

    assert (
        "title_changed"
        in migration
    )

    assert (
        "location_changed"
        in migration
    )

    assert (
        "salary_changed"
        in migration
    )

    assert (
        "days_active"
        in migration
    )
