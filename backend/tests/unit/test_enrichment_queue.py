from jobly.commands.bootstrap_enrichment import enqueue_bootstrap
from jobly.enrichment.schemas_v2 import JOB_ENRICHMENT_V2_JSON_SCHEMA, JobEnrichmentV2
from jobly.enrichment.worker import claim_next_queue_item, save_success


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = connection.rowcounts.pop(0) if connection.rowcounts else 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.connection.statements.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.connection.fetchone_values.pop(0) if self.connection.fetchone_values else None


class Connection:
    def __init__(self, *, fetchone_values=None, rowcounts=None):
        self.fetchone_values = list(fetchone_values or [])
        self.rowcounts = list(rowcounts or [])
        self.statements = []
        self.commits = 0

    def cursor(self, **_kwargs):
        return Cursor(self)

    def commit(self):
        self.commits += 1


def test_queue_claim_orders_new_then_changed_then_bootstrap():
    conn = Connection(fetchone_values=[None])
    assert claim_next_queue_item(conn) is None
    assert "ORDER BY priority ASC, created_at ASC" in conn.statements[0][0]


def test_queue_schema_prevents_duplicate_job_hash_pairs():
    migration = open("../migrations/008_enrichment_queue.sql", encoding="utf-8").read()
    assert "UNIQUE (job_id, content_hash)" in migration
    assert "CHECK (priority IN (1, 2, 3))" in migration


def test_v2_structured_schema_requires_every_dimension():
    assert set(JOB_ENRICHMENT_V2_JSON_SCHEMA["required"]) == set(
        JOB_ENRICHMENT_V2_JSON_SCHEMA["properties"]
    )


def test_bootstrap_is_idempotent_by_conflict_rule():
    first = Connection(rowcounts=[3])
    second = Connection(rowcounts=[0])
    assert enqueue_bootstrap(first, "v2") == 3
    assert enqueue_bootstrap(second, "v2") == 0
    assert "ON CONFLICT (job_id, content_hash) DO NOTHING" in first.statements[0][0]


def test_stale_enrichment_does_not_insert_result(monkeypatch):
    monkeypatch.setenv("AI_CLASSIFICATION_VERSION", "v2")
    classification = JobEnrichmentV2.model_construct(confidence=0.8)
    item = {"id": 4, "queue_id": 9, "queue_hash": "old-hash"}
    conn = Connection(fetchone_values=[("new-hash",)])
    assert save_success(conn, item, classification) is False
    statements = "\n".join(sql for sql, _params in conn.statements)
    assert "INSERT INTO job_enrichments" not in statements
    assert "stale_content_hash" in statements
