import argparse
import logging
import os

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from crawlers.db import get_connection

from crawlers.enrichment.classifier import (
    classify_job,
)

from crawlers.enrichment.input_builder import (
    build_classifier_payload,
)


CLASSIFICATION_VERSION = os.getenv(
    "AI_CLASSIFICATION_VERSION",
    "v1",
)

MAX_ATTEMPTS = int(
    os.getenv(
        "AI_MAX_ATTEMPTS",
        "5",
    )
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


def recover_stale_jobs(conn):
    """
    Recover jobs left in processing state
    if a worker crashed or was killed.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_status =
                    CASE
                        WHEN classification_attempts >= %s
                        THEN 'failed'
                        ELSE 'pending'
                    END,

                classification_started_at =
                    NULL,

                classification_error =
                    COALESCE(
                        classification_error,
                        'worker_timeout'
                    )

            WHERE
                classification_status =
                    'processing'

                AND classification_started_at
                    IS NOT NULL

                AND classification_started_at
                    < NOW()
                    - INTERVAL '15 minutes'
            """,
            (
                MAX_ATTEMPTS,
            ),
        )

    conn.commit()


def count_pending_fresh_jobs(conn):
    """
    Count jobs eligible for AI processing.

    Only jobs that are:
    - active
    - have a real posted_at
    - posted within the last 48 hours
    - pending classification
    - below retry limit
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT COUNT(*)

            FROM jobs

            WHERE
                active = TRUE

                AND posted_at IS NOT NULL

                AND posted_at >=
                    NOW() - INTERVAL '48 hours'

                AND content_hash IS NOT NULL

                AND classification_status =
                    'pending'

                AND classification_attempts < %s
            """,
            (
                MAX_ATTEMPTS,
            ),
        )

        row = cur.fetchone()

    return row[0]


def claim_next_job(conn):
    """
    Atomically claim one fresh pending job.

    FOR UPDATE SKIP LOCKED allows multiple
    workers to run later without processing
    the same job.
    """

    with conn.cursor(
        row_factory=dict_row
    ) as cur:

        cur.execute(
            """
            SELECT
                id,

                provider,
                company,
                title,
                location,

                employment_type,
                workplace_type,

                posted_at,
                posted_at_source,

                description_text,
                raw_payload,

                content_hash,

                classification_attempts

            FROM jobs

            WHERE
                active = TRUE

                AND posted_at IS NOT NULL

                AND posted_at >=
                    NOW() - INTERVAL '48 hours'

                AND content_hash IS NOT NULL

                AND classification_status =
                    'pending'

                AND classification_attempts
                    < %s

            ORDER BY
                posted_at DESC,
                id DESC

            FOR UPDATE
            SKIP LOCKED

            LIMIT 1
            """,
            (
                MAX_ATTEMPTS,
            ),
        )

        job = cur.fetchone()

        if job is None:
            conn.commit()

            return None

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_status =
                    'processing',

                classification_started_at =
                    NOW(),

                classification_attempts =
                    classification_attempts + 1,

                classification_error =
                    NULL

            WHERE id = %s
            """,
            (
                job["id"],
            ),
        )

        job[
            "classification_attempts"
        ] += 1

    conn.commit()

    return job


def reset_changed_job(
    conn,
    job_id: int,
):
    """
    The job changed while AI was processing it.

    Put the current database version back into
    pending state so the worker can classify
    the new content.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_status =
                    'pending',

                classification_started_at =
                    NULL,

                classification_error =
                    'job_changed_during_classification'

            WHERE id = %s
            """,
            (
                job_id,
            ),
        )

    conn.commit()


def save_success(
    conn,
    job: dict,
    classification,
):
    """
    Store AI classification only when the
    job content is still identical to what
    the AI classified.
    """

    locations = [
        location.model_dump()
        for location
        in classification.additional_locations
    ]

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                job_family = %s,

                job_subfamily = %s,

                related_roles = %s,

                skills = %s,

                seniority = %s,

                years_experience_min = %s,

                years_experience_max = %s,

                ai_locations = %s,

                classification_confidence =
                    %s,

                classification_status =
                    'ready',

                classification_version =
                    %s,

                classified_at =
                    NOW(),

                classified_content_hash =
                    content_hash,

                classification_started_at =
                    NULL,

                classification_error =
                    NULL

            WHERE
                id = %s

                AND content_hash = %s
            """,
            (
                classification.job_family,

                classification.job_subfamily,

                Jsonb(
                    classification.related_roles
                ),

                Jsonb(
                    classification.skills
                ),

                classification.seniority,

                classification.years_experience_min,

                classification.years_experience_max,

                Jsonb(
                    locations
                ),

                classification.confidence,

                CLASSIFICATION_VERSION,

                job["id"],

                job["content_hash"],
            ),
        )

        updated_rows = (
            cur.rowcount
        )

    conn.commit()

    if updated_rows == 0:

        logging.warning(
            (
                "STALE RESULT | "
                "job=%s | "
                "job changed while AI "
                "was processing it"
            ),
            job["id"],
        )

        reset_changed_job(
            conn,
            job["id"],
        )

        return False

    return True


def save_failure(
    conn,
    job: dict,
    error: Exception,
):
    """
    Retry failed AI processing until
    MAX_ATTEMPTS has been reached.
    """

    error_message = (
        str(error)[:2000]
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_status =
                    CASE

                        WHEN
                            classification_attempts
                            >= %s

                        THEN 'failed'

                        ELSE 'pending'

                    END,

                classification_started_at =
                    NULL,

                classification_error =
                    %s

            WHERE
                id = %s

                AND content_hash = %s
            """,
            (
                MAX_ATTEMPTS,

                error_message,

                job["id"],

                job["content_hash"],
            ),
        )

    conn.commit()


def process_job(
    conn,
    job: dict,
):
    payload = (
        build_classifier_payload(
            job
        )
    )

    logging.info(
        (
            "CLASSIFY | "
            "id=%s | "
            "provider=%s | "
            "posted_at=%s | "
            "title=%s"
        ),
        job["id"],
        job["provider"],
        job["posted_at"],
        job["title"],
    )

    classification = (
        classify_job(
            payload
        )
    )

    saved = save_success(
        conn,
        job,
        classification,
    )

    if not saved:
        return False

    logging.info(
        (
            "READY | "
            "id=%s | "
            "family=%s | "
            "subfamily=%s | "
            "seniority=%s | "
            "confidence=%.2f"
        ),

        job["id"],

        classification.job_family,

        classification.job_subfamily,

        classification.seniority,

        classification.confidence,
    )

    return True


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help=(
            "Maximum number of fresh "
            "jobs to classify this run"
        ),
    )

    args = parser.parse_args()

    if args.limit < 1:
        raise ValueError(
            "--limit must be at least 1"
        )

    processed = 0
    successful = 0
    failed = 0

    with get_connection() as conn:

        recover_stale_jobs(
            conn
        )

        pending_count = (
            count_pending_fresh_jobs(
                conn
            )
        )

        logging.info(
            (
                "FRESH PENDING JOBS | "
                "count=%s"
            ),
            pending_count,
        )

        print(
            "Fresh pending jobs:",
            pending_count,
        )

        while (
            processed < args.limit
        ):

            job = claim_next_job(
                conn
            )

            if job is None:

                logging.info(
                    "No fresh pending jobs"
                )

                break

            try:

                success = process_job(
                    conn,
                    job,
                )

                if success:
                    successful += 1

            except Exception as exc:

                failed += 1

                logging.exception(
                    "FAILED | id=%s",
                    job["id"],
                )

                save_failure(
                    conn,
                    job,
                    exc,
                )

            processed += 1

    logging.info(
        (
            "WORKER COMPLETE | "
            "processed=%s | "
            "successful=%s | "
            "failed=%s"
        ),
        processed,
        successful,
        failed,
    )

    print()
    print(
        "Processed:",
        processed,
    )
    print(
        "Successful:",
        successful,
    )
    print(
        "Failed:",
        failed,
    )


if __name__ == "__main__":
    main()