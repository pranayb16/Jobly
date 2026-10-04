from __future__ import annotations


def ensure_pipeline_run_table(
    conn,
) -> None:

    """
    Bootstrap run tracking before the ordered
    migration stage on a new database.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS
            pipeline_runs (

                id BIGSERIAL PRIMARY KEY,

                started_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW(),

                finished_at TIMESTAMPTZ,

                status TEXT
                    NOT NULL DEFAULT 'running',

                source_target INTEGER,

                sources_attempted INTEGER,

                sources_successful INTEGER,

                sources_failed INTEGER,

                jobs_seen INTEGER,

                jobs_new INTEGER,

                jobs_changed INTEGER,

                jobs_removed INTEGER,

                enrichments_processed INTEGER,

                enrichments_completed INTEGER,

                enrichments_failed INTEGER,

                enrichment_backlog INTEGER,

                snapshots_created INTEGER,

                company_stats_refreshed INTEGER,

                company_stats_publishable INTEGER,

                company_stats_unpublishable INTEGER,

                error TEXT,

                CONSTRAINT
                    pipeline_runs_status_check

                CHECK (
                    status IN (
                        'running',
                        'success',
                        'partial_success',
                        'failed'
                    )
                )
            )
            """
        )


        # Existing installations may have been
        # created before these metrics existed.

        cur.execute(
            """
            ALTER TABLE pipeline_runs

            ADD COLUMN IF NOT EXISTS
                company_stats_refreshed INTEGER
            """
        )


        cur.execute(
            """
            ALTER TABLE pipeline_runs

            ADD COLUMN IF NOT EXISTS
                company_stats_publishable INTEGER
            """
        )


        cur.execute(
            """
            ALTER TABLE pipeline_runs

            ADD COLUMN IF NOT EXISTS
                company_stats_unpublishable INTEGER
            """
        )


    conn.commit()


def create_pipeline_run(
    conn,
    source_target: int,
) -> int:

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO pipeline_runs (
                source_target
            )

            VALUES (%s)

            RETURNING id
            """,
            (
                source_target,
            ),
        )


        run_id = cur.fetchone()[0]


    conn.commit()


    return run_id


def finish_pipeline_run(
    conn,
    run_id: int,
    status: str,
    metrics: dict,
    error: str | None = None,
) -> None:

    fields = (

        "sources_attempted",

        "sources_successful",

        "sources_failed",

        "jobs_seen",

        "jobs_new",

        "jobs_changed",

        "jobs_removed",

        "enrichments_processed",

        "enrichments_completed",

        "enrichments_failed",

        "enrichment_backlog",

        "snapshots_created",

        "company_stats_refreshed",

        "company_stats_publishable",

        "company_stats_unpublishable",
    )


    values = [
        metrics.get(
            field,
            0,
        )

        for field
        in fields
    ]


    assignments = ", ".join(
        f"{field} = %s"
        for field
        in fields
    )


    with conn.cursor() as cur:

        cur.execute(
            f"""
            UPDATE pipeline_runs

            SET
                finished_at = NOW(),

                status = %s,

                {assignments},

                error = %s

            WHERE id = %s
            """,
            (
                status,
                *values,

                (
                    error[:2000]
                    if error
                    else None
                ),

                run_id,
            ),
        )


    conn.commit()