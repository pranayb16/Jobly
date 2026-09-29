import json
import logging

from crawlers.db import get_connection
from crawlers.runner import crawl_source


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
            raw_payload
        )

        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )

        ON CONFLICT (
            source_id,
            external_job_id
        )

        DO UPDATE SET

            title =
                EXCLUDED.title,

            location =
                EXCLUDED.location,

            employment_type =
                EXCLUDED.employment_type,

            workplace_type =
                EXCLUDED.workplace_type,

            posted_at =
                EXCLUDED.posted_at,

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
            json.dumps(job.raw),
        ),
    )


def main():

    with get_connection() as conn:

        with conn.cursor() as cur:

            # Only 50 initially
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
                    "[%s/%s] FAILED | %s | %s",
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