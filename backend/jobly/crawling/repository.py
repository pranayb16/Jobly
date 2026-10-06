from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlSource:
    id: int
    provider: str
    canonical_url: str
    last_success_at: object
    last_job_count: int | None
    company_id: int | None
    company_name: str | None


CRAWL_SOURCE_LOCK_NAMESPACE = 170010001


def acquire_source_lock(conn, source_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_try_advisory_lock(%s, %s)",
            (CRAWL_SOURCE_LOCK_NAMESPACE, source_id),
        )
        row = cur.fetchone()
    return bool(row and row[0])


def release_source_lock(conn, source_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_advisory_unlock(%s, %s)",
            (CRAWL_SOURCE_LOCK_NAMESPACE, source_id),
        )


def select_active_sources(cur, limit: int | None) -> list[CrawlSource]:
    if limit is None:
        cur.execute(
            """
            SELECT s.id, s.provider, s.canonical_url, s.last_success_at,
                   s.last_job_count, s.company_id, c.name
            FROM sources AS s
            LEFT JOIN companies AS c ON c.id = s.company_id
            WHERE s.status = 'active'
            ORDER BY s.id
            """
        )
    else:
        cur.execute(
            """
            SELECT s.id, s.provider, s.canonical_url, s.last_success_at,
                   s.last_job_count, s.company_id, c.name
            FROM sources AS s
            LEFT JOIN companies AS c ON c.id = s.company_id
            WHERE s.status = 'active'
            ORDER BY s.id
            LIMIT %s
            """,
            (limit,),
        )
    return [CrawlSource(*row) for row in cur.fetchall()]


def create_crawl_run(
    conn, source_id: int, pipeline_run_id: int | None = None
) -> tuple[int, object]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crawl_runs (source_id, status, pipeline_run_id)
            VALUES (%s, 'running', %s)
            RETURNING id, started_at
            """,
            (source_id, pipeline_run_id),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0], row[1]


def mark_crawl_success(
    cur,
    source_id: int,
    crawl_run_id: int,
    job_count: int,
    *,
    warning: str | None = None,
    update_trusted_count: bool = True,
) -> None:
    cur.execute(
        """
        UPDATE sources
        SET last_attempt_at = NOW(), last_crawled_at = NOW(), last_success_at = NOW(),
            last_job_count = CASE WHEN %s THEN %s ELSE last_job_count END,
            consecutive_failures = 0, last_error = NULL
        WHERE id = %s
        """,
        (update_trusted_count, job_count, source_id),
    )
    cur.execute(
        """
        UPDATE crawl_runs
        SET status = 'success', finished_at = NOW(), job_count = %s, error = NULL,
            deactivation_skipped = %s, warning = %s
        WHERE id = %s
        """,
        (job_count, warning is not None, warning, crawl_run_id),
    )


def mark_crawl_failed(conn, source_id: int, crawl_run_id: int, error: Exception) -> None:
    error_message = str(error)[:2000]
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sources
            SET
                status = CASE
                    WHEN consecutive_failures + 1 >= 3
                        THEN 'inactive'
                    ELSE status
                END,
                last_attempt_at = NOW(),
                last_failure_at = NOW(),
                consecutive_failures = consecutive_failures + 1,
                last_error = %s
            WHERE id = %s
            """,
            (error_message, source_id),
        )
        cur.execute(
            """
            UPDATE crawl_runs
            SET status = 'failed', finished_at = NOW(), error = %s
            WHERE id = %s
            """,
            (error_message, crawl_run_id),
        )
    conn.commit()
