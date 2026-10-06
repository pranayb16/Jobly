from __future__ import annotations

from datetime import datetime

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from jobly.db.pool import get_pool
from jobly.products.jobs.schemas import (
    JobDetail,
    JobListItem,
    JobsResponse,
)


router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
)


STRING_LIST_FIELDS = (
    "related_roles",
    "role_keywords",
    "responsibility_tags",
    "skills",
    "required_skills",
    "preferred_skills",
    "soft_skills",
    "education_fields",
    "certifications",
)


def _normalize_canonical_row(row: dict) -> dict:
    """Keep legacy JSON objects/nulls from breaking the typed jobs response."""
    result = dict(row)

    for field in STRING_LIST_FIELDS:
        value = result.get(field)
        if isinstance(value, dict):
            result[field] = list(value)
        elif not isinstance(value, list):
            result[field] = []

    for field in ("locations", "preferred_locations", "ai_locations"):
        if not isinstance(result.get(field), list):
            result[field] = []

    return result


CANONICAL_SELECT = """
    cji.*,

    cji.job_id AS id,

    cji.company_name AS company,

    cji.original_title AS title,

    LEFT(
        cji.description_text,
        300
    ) AS description_excerpt,

    cji.locations AS ai_locations
"""


@router.get(
    "",
    response_model=JobsResponse,
)
def get_jobs(
    limit: int = Query(
        default=20,
        ge=1,
        le=5000,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    posted_since: datetime | None = Query(default=None),
) -> JobsResponse:

    with (
        get_pool()
        .connection()
    ) as conn:

        with conn.cursor() as cur:

            # Keep the old publication gate for the optional
            # job-board product.
            #
            # public_jobs still controls:
            # - active
            # - U.S.
            # - classification ready
            # - current content
            # - recent posting
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM public_jobs
                WHERE (%s::timestamptz IS NULL OR posted_at >= %s)
                """,
                (posted_since, posted_since),
            )

            total = (
                cur.fetchone()["total"]
            )

            cur.execute(
                f"""
                SELECT
                    {CANONICAL_SELECT}

                FROM public_jobs AS public

                JOIN current_job_intelligence AS cji
                  ON cji.job_id = public.id

                WHERE (%s::timestamptz IS NULL OR cji.posted_at >= %s)

                ORDER BY
                    COALESCE(
                        cji.posted_at,
                        cji.first_seen_at
                    ) DESC,
                    cji.job_id DESC

                LIMIT %s
                OFFSET %s
                """,
                (
                    posted_since,
                    posted_since,
                    limit,
                    offset,
                ),
            )

            rows = cur.fetchall()

    return JobsResponse(
        count=total,
        limit=limit,
        offset=offset,
        jobs=[
            JobListItem(
                **_normalize_canonical_row(row)
            )
            for row in rows
        ],
    )


@router.get(
    "/{job_id}",
    response_model=JobDetail,
)
def get_job(
    job_id: int,
) -> JobDetail:

    with (
        get_pool()
        .connection()
    ) as conn:

        with conn.cursor() as cur:

            cur.execute(
                f"""
                SELECT
                    {CANONICAL_SELECT}

                FROM public_jobs AS public

                JOIN current_job_intelligence AS cji
                  ON cji.job_id = public.id

                WHERE public.id = %s

                LIMIT 1
                """,
                (
                    job_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return JobDetail(
        **_normalize_canonical_row(row)
    )
