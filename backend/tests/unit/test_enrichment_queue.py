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
    save_success,
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
        "ORDER BY priority ASC, created_at ASC"
        in conn.statements[0][0]
    )


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
        "ON CONFLICT ( job_id, content_hash )"
        in normalized_sql
        or
        "ON CONFLICT (job_id, content_hash)"
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