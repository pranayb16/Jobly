from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row

from jobly.db.pool import get_pool
from jobly.intelligence import MIN_AI_COVERAGE
from jobly.intelligence.repository import aggregate_dimension, market_snapshot


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def skills(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    with get_pool().connection() as conn:
        market = market_snapshot(conn)
        total = market["total_open_jobs"]
        coverage = market["enriched_jobs"] / total if total else 0.0
        items = aggregate_dimension(conn, "skill_counts", limit) if coverage >= MIN_AI_COVERAGE else []
    return {"skills": items, "enrichment_coverage": coverage,
            "available": coverage >= MIN_AI_COVERAGE}


@router.get("/{skill}")
def skill_detail(skill: str) -> dict:
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                WITH latest AS (SELECT MAX(snapshot_date) AS day FROM company_daily_snapshots)
                SELECT c.name AS company, c.slug, (s.skill_counts ->> %s)::integer AS count,
                       s.snapshot_date, s.enrichment_coverage
                FROM company_daily_snapshots AS s
                JOIN latest ON s.snapshot_date = latest.day
                JOIN companies AS c ON c.id = s.company_id
                WHERE s.skill_counts ? %s AND s.enrichment_coverage >= %s
                ORDER BY count DESC, c.name
                """,
                (skill, skill, MIN_AI_COVERAGE),
            )
            companies = list(cur.fetchall())
    if not companies:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"skill": skill, "count": sum(row["count"] for row in companies), "companies": companies}
