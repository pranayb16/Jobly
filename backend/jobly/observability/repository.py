from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from jobly.db.connection import (
    get_connection,
)


def start_stage(
    pipeline_run_id: int,
    stage: str,
) -> None:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO pipeline_stage_runs (
                    pipeline_run_id,
                    stage,
                    status,
                    started_at,
                    finished_at,
                    metrics,
                    error
                )

                VALUES (
                    %s,
                    %s,
                    'running',
                    NOW(),
                    NULL,
                    '{}'::jsonb,
                    NULL
                )

                ON CONFLICT (
                    pipeline_run_id,
                    stage
                )

                DO UPDATE SET
                    status = 'running',
                    started_at = NOW(),
                    finished_at = NULL,
                    metrics = '{}'::jsonb,
                    error = NULL
                """,
                (
                    pipeline_run_id,
                    stage,
                ),
            )

        conn.commit()


def finish_stage(
    pipeline_run_id: int,
    stage: str,
    *,
    status: str = "success",
    metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_stage_runs

                SET
                    status = %s,
                    finished_at = NOW(),
                    metrics = %s,
                    error = %s

                WHERE pipeline_run_id = %s
                  AND stage = %s
                """,
                (
                    status,
                    Jsonb(
                        metrics or {}
                    ),
                    (
                        error[:4000]
                        if error
                        else None
                    ),
                    pipeline_run_id,
                    stage,
                ),
            )

        conn.commit()


def record_event(
    *,
    pipeline_run_id: int | None,
    stage: str | None,
    severity: str,
    event_type: str,
    message: str,
    source_id: int | None = None,
    job_id: int | None = None,
    queue_id: int | None = None,
    provider: str | None = None,
    model: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:

    if pipeline_run_id is None:
        return

    try:

        with get_connection() as conn:

            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO pipeline_events (
                        pipeline_run_id,
                        stage,
                        severity,
                        event_type,

                        source_id,
                        job_id,
                        queue_id,

                        provider,
                        model,

                        message,
                        details
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,

                        %s,
                        %s,
                        %s,

                        %s,
                        %s,

                        %s,
                        %s
                    )
                    """,
                    (
                        pipeline_run_id,
                        stage,
                        severity,
                        event_type,

                        source_id,
                        job_id,
                        queue_id,

                        provider,
                        model,

                        message[:4000],

                        Jsonb(
                            details or {}
                        ),
                    ),
                )

            conn.commit()

    except Exception:
        # Observability must never crash
        # the actual pipeline.
        return