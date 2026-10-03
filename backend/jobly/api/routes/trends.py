from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter
from psycopg.rows import dict_row

from jobly.db.pool import get_pool
from jobly.intelligence import MIN_AI_COVERAGE
from jobly.intelligence.repository import aggregate_dimension, market_snapshot
from jobly.intelligence.trends import change_between


router = APIRouter(prefix="/api/trends", tags=["trends"])


def _market_total_on(conn, day):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT SUM(total_open_jobs) AS total
            FROM company_daily_snapshots WHERE snapshot_date = %s
            """,
            (day,),
        )
        return cur.fetchone()["total"]


@router.get("")
def trends() -> dict:
    with get_pool().connection() as conn:
        latest = market_snapshot(conn)
        day = latest["snapshot_date"]
        seven = _market_total_on(conn, day - timedelta(days=7)) if day else None
        thirty = _market_total_on(conn, day - timedelta(days=30)) if day else None
        total = latest["total_open_jobs"]
        coverage = (latest["enriched_jobs"] / total) if total else 0.0
        aggregates_available = coverage >= MIN_AI_COVERAGE
        roles = aggregate_dimension(conn, "role_counts", 10) if aggregates_available else None
        skills = aggregate_dimension(conn, "skill_counts", 10) if aggregates_available else None
    return {
        **latest,
        "enrichment_coverage": coverage,
        "ai_aggregates_available": aggregates_available,
        "change_7d": change_between(total, seven),
        "change_30d": change_between(total, thirty),
        "top_roles": roles,
        "top_skills": skills,
    }
