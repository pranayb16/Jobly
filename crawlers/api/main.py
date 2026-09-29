import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from crawlers.api.db import pool
from crawlers.api.schemas import (
    JobDetail,
    JobListItem,
    JobsResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    pool.wait()

    yield

    pool.close()


app = FastAPI(
    title="Jobly API",
    version="1.0.0",
    lifespan=lifespan,
)


frontend_origin = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:3000",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_origin,
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

            cur.fetchone()

    return {
        "status": "ok",
    }


@app.get(
    "/api/jobs",
    response_model=JobsResponse,
)
def get_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    with pool.connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM jobs
                WHERE active = TRUE
                  AND posted_at IS NOT NULL
                  AND posted_at >= NOW() - INTERVAL '48 hours'
                """
            )

            total = cur.fetchone()["total"]

            cur.execute(
                """
                SELECT
                    id,
                    external_job_id,
                    provider,
                    company,
                    title,
                    location,
                    employment_type,
                    workplace_type,
                    LEFT(description_text, 300)
                        AS description_excerpt,
                    posted_at,
                    posted_at_source,
                    job_url,
                    apply_url,
                    first_seen_at,
                    last_seen_at
                FROM jobs
                WHERE active = TRUE
                  AND posted_at IS NOT NULL
                  AND posted_at >= NOW() - INTERVAL '48 hours'
                ORDER BY
                    posted_at DESC,
                    id DESC
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
            JobListItem(**row)
            for row in rows
        ],
    )

@app.get(
    "/api/jobs/{job_id}",
    response_model=JobDetail,
)
def get_job(job_id: int):
    with pool.connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    external_job_id,
                    provider,
                    company,
                    title,
                    location,
                    employment_type,
                    workplace_type,
                    posted_at,
                    posted_at_source,
                    description_text,
                    description_html,
                    job_url,
                    apply_url,
                    first_seen_at,
                    last_seen_at

                FROM jobs

                WHERE id = %s
                AND active = TRUE
                AND posted_at IS NOT NULL
                AND posted_at >= NOW() - INTERVAL '48 hours'

                LIMIT 1
                """,
                (job_id,),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return JobDetail(**row)