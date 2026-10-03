from fastapi import APIRouter, HTTPException, Query

from jobly.db.pool import get_pool
from jobly.products.jobs.schemas import JobDetail, JobListItem, JobsResponse


router = APIRouter(prefix="/api/jobs", tags=["jobs"])

LIST_COLUMNS = """
    id, external_job_id, provider, company, title, location,
    employment_type, workplace_type,
    LEFT(description_text, 300) AS description_excerpt,
    posted_at, posted_at_source, job_url, apply_url, first_seen_at, last_seen_at,
    job_family, job_subfamily, related_roles, skills, seniority,
    years_experience_min, years_experience_max, ai_locations, classification_confidence
"""


@router.get("", response_model=JobsResponse)
def get_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobsResponse:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM public_jobs")
            total = cur.fetchone()["total"]
            cur.execute(
                f"""
                SELECT {LIST_COLUMNS}
                FROM public_jobs
                ORDER BY posted_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
    return JobsResponse(
        count=total,
        limit=limit,
        offset=offset,
        jobs=[JobListItem(**row) for row in rows],
    )


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int) -> JobDetail:
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {LIST_COLUMNS}, description_text, description_html
                FROM public_jobs
                WHERE id = %s
                LIMIT 1
                """,
                (job_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail(**row)
