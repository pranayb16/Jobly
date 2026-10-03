from __future__ import annotations

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
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
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
                """
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
                **row
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
        **row
    )