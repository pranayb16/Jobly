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
    job,
):

    content_hash = build_content_hash(
        job
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

            description_text,
            description_html,

            job_url,
            apply_url,

            raw_payload,

            content_hash,

            classification_status
        )

        VALUES (
            %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s,
            %s,
            'pending'
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

            job.description.text,
            job.description.html,

            job.job_url,
            job.apply_url,

            Jsonb(job.raw),

            content_hash,
        ),
    )


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            # Intentionally use the same first
            # 50 sources during early development.
            cur.execute(
                """
                SELECT
                    id,
                    provider,
                    canonical_url

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

            logging.info(
                "[%s/%s] START | %s | %s",
                index,
                len(sources),
                provider,
                career_url,
            )

            try:

                jobs = crawl_source(
                    provider,
                    career_url,
                )

                with conn.cursor() as cur:

                    for job in jobs:

                        save_job(
                            cur,
                            source_id,
                            job,
                        )

                    cur.execute(
                        """
                        UPDATE sources

                        SET
                            last_crawled_at = NOW(),
                            last_success_at = NOW(),
                            last_job_count = %s

                        WHERE id = %s
                        """,

                        (
                            len(jobs),
                            source_id,
                        ),
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

            except Exception:

                conn.rollback()

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