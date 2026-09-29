import logging

from psycopg.types.json import Jsonb

from crawlers.db import get_connection
from crawlers.runner import crawl_source

from crawlers.enrichment.input_builder import (
    build_content_hash,
)


logging.basicConfig(
    filename="crawler.log",
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


def save_job(
    cur,
    source_id: int,
    crawl_run_id: int,
    previous_success_at,
    crawl_started_at,
    job,
):
    content_hash = build_content_hash(
        job
    )

    observed_new_after = None
    observed_new_before = None

    # Providers such as Lever may not give us a trustworthy
    # employer publication timestamp.
    #
    # If this is a job without posted_at, record the interval
    # in which Jobly first observed it.
    if (
        job.posted_at is None
        and previous_success_at is not None
    ):
        observed_new_after = (
            previous_success_at
        )

        observed_new_before = (
            crawl_started_at
        )

    cur.execute(
        """
        INSERT INTO jobs (
            source_id,
            external_job_id,

            provider,
            company,
            title,
            location,

            employment_type,
            workplace_type,

            posted_at,
            posted_at_source,

            observed_new_after,
            observed_new_before,

            description_text,
            description_html,

            job_url,
            apply_url,

            raw_payload,

            content_hash,

            classification_status,

            last_seen_crawl_id
        )

        VALUES (
            %s, %s,

            %s, %s, %s, %s,

            %s, %s,

            %s, %s,

            %s, %s,

            %s, %s,

            %s, %s,

            %s,

            %s,

            'pending',

            %s
        )

        ON CONFLICT (
            source_id,
            external_job_id
        )

        DO UPDATE SET

            provider =
                EXCLUDED.provider,

            company =
                EXCLUDED.company,

            title =
                EXCLUDED.title,

            location =
                EXCLUDED.location,

            employment_type =
                EXCLUDED.employment_type,

            workplace_type =
                EXCLUDED.workplace_type,

            posted_at =
                COALESCE(
                    EXCLUDED.posted_at,
                    jobs.posted_at
                ),

            posted_at_source =
                COALESCE(
                    EXCLUDED.posted_at_source,
                    jobs.posted_at_source
                ),

            observed_new_after =
                COALESCE(
                    jobs.observed_new_after,
                    EXCLUDED.observed_new_after
                ),

            observed_new_before =
                COALESCE(
                    jobs.observed_new_before,
                    EXCLUDED.observed_new_before
                ),

            description_text =
                EXCLUDED.description_text,

            description_html =
                EXCLUDED.description_html,

            job_url =
                EXCLUDED.job_url,

            apply_url =
                EXCLUDED.apply_url,

            raw_payload =
                EXCLUDED.raw_payload,

            classification_status =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN 'pending'

                    ELSE
                        jobs.classification_status

                END,

            classification_started_at =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN NULL

                    ELSE
                        jobs.classification_started_at

                END,

            classification_attempts =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN 0

                    ELSE
                        jobs.classification_attempts

                END,

            classification_error =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN NULL

                    ELSE
                        jobs.classification_error

                END,

            classified_at =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN NULL

                    ELSE
                        jobs.classified_at

                END,

            classified_content_hash =
                CASE

                    WHEN
                        jobs.content_hash
                        IS DISTINCT FROM
                        EXCLUDED.content_hash

                    THEN NULL

                    ELSE
                        jobs.classified_content_hash

                END,

            content_hash =
                EXCLUDED.content_hash,

            last_seen_at =
                NOW(),

            last_seen_crawl_id =
                EXCLUDED.last_seen_crawl_id,

            removed_at =
                NULL,

            active =
                TRUE
        """,
        (
            source_id,
            job.external_job_id,

            job.provider,
            job.company,
            job.title,
            job.location,

            job.employment_type,
            job.workplace_type,

            job.posted_at,
            job.posted_at_source,

            observed_new_after,
            observed_new_before,

            job.description.text,
            job.description.html,

            job.job_url,
            job.apply_url,

            Jsonb(job.raw),

            content_hash,

            crawl_run_id,
        ),
    )


def create_crawl_run(
    conn,
    source_id: int,
):
    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO crawl_runs (
                source_id,
                status
            )

            VALUES (
                %s,
                'running'
            )

            RETURNING
                id,
                started_at
            """,
            (
                source_id,
            ),
        )

        row = cur.fetchone()

    conn.commit()

    return (
        row[0],
        row[1],
    )


def mark_missing_jobs_inactive(
    cur,
    source_id: int,
    crawl_run_id: int,
    previous_job_count,
    current_job_count: int,
):
    # Safety guard:
    #
    # If a source previously returned jobs but now suddenly
    # returns zero, do not immediately close every job.
    #
    # Treat that as suspicious and require another successful
    # crawl before mass-deactivation logic is considered.
    if (
        previous_job_count is not None
        and previous_job_count > 0
        and current_job_count == 0
    ):
        logging.warning(
            "SKIP DEACTIVATION | "
            "source_id=%s | "
            "previous_jobs=%s | "
            "current_jobs=0",
            source_id,
            previous_job_count,
        )

        return

    cur.execute(
        """
        UPDATE jobs

        SET
            active = FALSE,
            removed_at = NOW()

        WHERE source_id = %s

          AND active = TRUE

          AND (
              last_seen_crawl_id IS NULL
              OR last_seen_crawl_id <> %s
          )
        """,
        (
            source_id,
            crawl_run_id,
        ),
    )


def mark_crawl_success(
    cur,
    source_id: int,
    crawl_run_id: int,
    job_count: int,
):
    cur.execute(
        """
        UPDATE sources

        SET
            last_attempt_at = NOW(),
            last_crawled_at = NOW(),
            last_success_at = NOW(),
            last_job_count = %s,

            consecutive_failures = 0,
            last_error = NULL

        WHERE id = %s
        """,
        (
            job_count,
            source_id,
        ),
    )

    cur.execute(
        """
        UPDATE crawl_runs

        SET
            status = 'success',
            finished_at = NOW(),
            job_count = %s,
            error = NULL

        WHERE id = %s
        """,
        (
            job_count,
            crawl_run_id,
        ),
    )


def mark_crawl_failed(
    conn,
    source_id: int,
    crawl_run_id: int,
    error: Exception,
):
    error_message = str(error)

    if len(error_message) > 2000:
        error_message = (
            error_message[:2000]
        )

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE sources

            SET
                last_attempt_at = NOW(),
                last_failure_at = NOW(),

                consecutive_failures =
                    consecutive_failures + 1,

                last_error = %s

            WHERE id = %s
            """,
            (
                error_message,
                source_id,
            ),
        )

        cur.execute(
            """
            UPDATE crawl_runs

            SET
                status = 'failed',
                finished_at = NOW(),
                error = %s

            WHERE id = %s
            """,
            (
                error_message,
                crawl_run_id,
            ),
        )

    conn.commit()


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            # Intentionally crawl the same first
            # 50 active sources during early development.
            cur.execute(
                """
                SELECT
                    id,
                    provider,
                    canonical_url,
                    last_success_at,
                    last_job_count

                FROM sources

                WHERE status = 'active'

                ORDER BY id

                LIMIT 50
                """
            )

            sources = cur.fetchall()

        logging.info(
            "CRAWL START | sources=%s",
            len(sources),
        )

        for index, source in enumerate(
            sources,
            start=1,
        ):

            source_id = source[0]
            provider = source[1]
            career_url = source[2]

            previous_success_at = (
                source[3]
            )

            previous_job_count = (
                source[4]
            )

            crawl_run_id = None

            logging.info(
                "[%s/%s] START | %s | %s",
                index,
                len(sources),
                provider,
                career_url,
            )

            try:

                (
                    crawl_run_id,
                    crawl_started_at,
                ) = create_crawl_run(
                    conn,
                    source_id,
                )

                jobs = crawl_source(
                    provider,
                    career_url,
                )

                with conn.cursor() as cur:

                    for job in jobs:

                        save_job(
                            cur,
                            source_id,
                            crawl_run_id,
                            previous_success_at,
                            crawl_started_at,
                            job,
                        )

                    mark_missing_jobs_inactive(
                        cur,
                        source_id,
                        crawl_run_id,
                        previous_job_count,
                        len(jobs),
                    )

                    mark_crawl_success(
                        cur,
                        source_id,
                        crawl_run_id,
                        len(jobs),
                    )

                conn.commit()

                logging.info(
                    "[%s/%s] SUCCESS | "
                    "%s | jobs=%s",
                    index,
                    len(sources),
                    provider,
                    len(jobs),
                )

            except Exception as exc:

                conn.rollback()

                if crawl_run_id is not None:

                    try:
                        mark_crawl_failed(
                            conn,
                            source_id,
                            crawl_run_id,
                            exc,
                        )

                    except Exception:

                        conn.rollback()

                        logging.exception(
                            "FAILED TO RECORD "
                            "CRAWL FAILURE | "
                            "source_id=%s | "
                            "crawl_run_id=%s",
                            source_id,
                            crawl_run_id,
                        )

                logging.exception(
                    "[%s/%s] FAILED | "
                    "%s | %s",
                    index,
                    len(sources),
                    provider,
                    career_url,
                )

        logging.info(
            "CRAWL COMPLETE"
        )


if __name__ == "__main__":
    main()