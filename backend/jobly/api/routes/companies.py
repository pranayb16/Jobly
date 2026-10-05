from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query

from jobly.db.pool import get_pool
from jobly.intelligence.repository import (
    company_history,
    get_company,
    get_company_hiring_stats,
    list_companies,
)
from jobly.intelligence.trends import change_between


router = APIRouter(prefix="/api/companies", tags=["companies"])


def _trend_payload(history: list[dict]) -> dict:
    if not history:
        return {"latest": None, "change_7d": None, "change_30d": None, "history": []}
    latest = history[0]
    by_date = {row["snapshot_date"]: row for row in history}
    seven = by_date.get(latest["snapshot_date"] - timedelta(days=7))
    thirty = by_date.get(latest["snapshot_date"] - timedelta(days=30))
    return {
        "latest": latest,
        "change_7d": change_between(latest["total_open_jobs"], seven["total_open_jobs"] if seven else None),
        "change_30d": change_between(latest["total_open_jobs"], thirty["total_open_jobs"] if thirty else None),
        "history": history,
    }


@router.get("")
def companies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with get_pool().connection() as conn:
        total, rows = list_companies(conn, limit=limit, offset=offset)
    return {"count": total, "limit": limit, "offset": offset,
            "companies": rows}


@router.get("/{slug}")
def company(slug: str) -> dict:
    with get_pool().connection() as conn:
        row = get_company_hiring_stats(conn, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return row


@router.get("/{slug}/trends")
def company_trends(slug: str) -> dict:
    with get_pool().connection() as conn:
        row = get_company(conn, slug)
        if row is None:
            raise HTTPException(status_code=404, detail="Company not found")
        history = company_history(conn, row["id"])
    return {"company": {"name": row["name"], "slug": row["slug"]}, **_trend_payload(history)}
