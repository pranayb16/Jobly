from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlSource:
    id: int
    provider: str
    canonical_url: str
    last_success_at: object
    last_job_count: int | None


def select_active_sources(cur, limit: int | None) -> list[CrawlSource]:
    if limit is None:
        cur.execute(
            """
            SELECT id, provider, canonical_url, last_success_at, last_job_count
            FROM sources
            WHERE status = 'active'
            ORDER BY id
            """
        )
    else:
        cur.execute(
            """
            SELECT id, provider, canonical_url, last_success_at, last_job_count
            FROM sources
            WHERE status = 'active'
            ORDER BY id
            LIMIT %s
            """,
            (limit,),
        )
    return [CrawlSource(*row) for row in cur.fetchall()]


def create_crawl_run(conn, source_id: int) -> tuple[int, object]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO crawl_runs (source_id, status)
            VALUES (%s, 'running')
            RETURNING id, started_at
            """,
            (source_id,),
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
) -> None:
    cur.execute(
        """
        UPDATE sources
        SET last_attempt_at = NOW(), last_crawled_at = NOW(), last_success_at = NOW(),
            last_job_count = %s, consecutive_failures = 0, last_error = NULL
        WHERE id = %s
        """,
        (job_count, source_id),
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
            SET last_attempt_at = NOW(), last_failure_at = NOW(),
                consecutive_failures = consecutive_failures + 1, last_error = %s
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
