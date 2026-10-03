from fastapi import APIRouter, HTTPException

from jobly.config import get_settings
from jobly.db.pool import get_pool


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    return {"status": "ok"}


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM schema_migrations LIMIT 1")
                cur.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database is not ready") from exc
    return {"status": "ready"}


@router.get("/health/system")
def system_health() -> dict:
    settings = get_settings()
    try:
        with get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, finished_at FROM pipeline_runs
                    ORDER BY started_at DESC LIMIT 1
                    """
                )
                pipeline = cur.fetchone()
                cur.execute("SELECT COUNT(*) AS count FROM sources WHERE status = 'active'")
                active_sources = cur.fetchone()["count"]
                cur.execute("SELECT COUNT(*) AS count FROM enrichment_queue WHERE status = 'pending'")
                backlog = cur.fetchone()["count"]
                cur.execute("SELECT MAX(snapshot_date) AS day FROM company_daily_snapshots")
                latest_snapshot = cur.fetchone()["day"]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="system health unavailable") from exc
    return {
        "status": "ok" if pipeline and pipeline["status"] in {"success", "partial_success"} else "degraded",
        "last_pipeline_status": pipeline["status"] if pipeline else None,
        "last_pipeline_finish_time": pipeline["finished_at"] if pipeline else None,
        "active_source_count": active_sources,
        "source_target_count": settings.source_target_count,
        "enrichment_backlog": backlog,
        "latest_snapshot_date": latest_snapshot,
    }
