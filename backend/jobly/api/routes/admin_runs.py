from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from jobly.db.pool import get_pool


router = APIRouter(prefix="/api/admin/runs", tags=["admin-runs"])


RUN_COLUMNS = """
    id,
    status,
    started_at,
    finished_at,
    EXTRACT(
        EPOCH FROM (COALESCE(finished_at, NOW()) - started_at)
    )::double precision AS duration_seconds,
    source_target,
    sources_attempted,
    sources_successful,
    sources_failed,
    jobs_seen,
    jobs_new,
    jobs_changed,
    jobs_removed,
    enrichments_processed,
    enrichments_completed,
    enrichments_failed,
    enrichment_backlog,
    snapshots_created,
    company_stats_refreshed,
    company_stats_publishable,
    company_stats_unpublishable,
    error
"""


def _get_run(conn, run_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {RUN_COLUMNS}
            FROM pipeline_runs
            WHERE id = %s
            """,
            (run_id,),
        )
        return cur.fetchone()


@router.get("")
def list_runs(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM pipeline_runs")
            count = cur.fetchone()["count"]
            cur.execute(
                f"""
                SELECT {RUN_COLUMNS}
                FROM pipeline_runs
                ORDER BY started_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            runs = list(cur.fetchall())

    return {"count": count, "limit": limit, "offset": offset, "runs": runs}


@router.get("/{run_id}")
def get_run(run_id: int) -> dict:
    with get_pool().connection() as conn:
        run = _get_run(conn, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT stage,
                       status,
                       started_at,
                       finished_at,
                       EXTRACT(
                           EPOCH FROM (COALESCE(finished_at, NOW()) - started_at)
                       )::double precision AS duration_seconds,
                       metrics,
                       error
                FROM pipeline_stage_runs
                WHERE pipeline_run_id = %s
                ORDER BY started_at, id
                """,
                (run_id,),
            )
            stages = list(cur.fetchall())

            cur.execute(
                """
                SELECT id,
                       stage,
                       severity,
                       event_type,
                       source_id,
                       job_id,
                       queue_id,
                       provider,
                       model,
                       message,
                       details,
                       created_at
                FROM pipeline_events
                WHERE pipeline_run_id = %s
                ORDER BY created_at, id
                """,
                (run_id,),
            )
            events = list(cur.fetchall())

            cur.execute(
                """
                SELECT cr.id AS crawl_run_id,
                       cr.source_id,
                       s.provider,
                       s.canonical_url,
                       s.company_id,
                       c.name AS company_name,
                       cr.status,
                       cr.started_at,
                       cr.finished_at,
                       EXTRACT(
                           EPOCH FROM (COALESCE(cr.finished_at, NOW()) - cr.started_at)
                       )::double precision AS duration_seconds,
                       cr.job_count,
                       cr.deactivation_skipped,
                       cr.warning,
                       cr.error
                FROM crawl_runs AS cr
                LEFT JOIN sources AS s
                  ON s.id = cr.source_id
                LEFT JOIN companies AS c
                  ON c.id = s.company_id
                WHERE cr.pipeline_run_id = %s
                ORDER BY cr.started_at, cr.id
                """,
                (run_id,),
            )
            crawl_runs = list(cur.fetchall())

    return {"run": run, "stages": stages, "events": events, "crawl_runs": crawl_runs}


@router.get("/{run_id}/logs")
def get_run_logs(
    run_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    stage: str | None = Query(default=None, min_length=1, max_length=100),
    level: str | None = Query(default=None, min_length=1, max_length=50),
) -> dict:
    with get_pool().connection() as conn:
        if _get_run(conn, run_id) is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        filters = ["pipeline_run_id = %s"]
        values: list[object] = [run_id]

        if stage is not None:
            filters.append("stage = %s")
            values.append(stage)
        if level is not None:
            filters.append("UPPER(level) = UPPER(%s)")
            values.append(level)

        where_clause = " AND ".join(filters)

        with conn.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS count FROM pipeline_logs WHERE {where_clause}",
                tuple(values),
            )
            count = cur.fetchone()["count"]
            cur.execute(
                f"""
                SELECT id, stage, created_at, level, logger, message, exception
                FROM pipeline_logs
                WHERE {where_clause}
                ORDER BY created_at, id
                LIMIT %s OFFSET %s
                """,
                (*values, limit, offset),
            )
            logs = list(cur.fetchall())

    return {"count": count, "limit": limit, "offset": offset, "logs": logs}
