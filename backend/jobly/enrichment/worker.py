import argparse
import logging

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobly.config import get_settings
from jobly.db.connection import (
    get_connection,
)

from jobly.enrichment.classifier import (
    classify_job,
)

from jobly.enrichment.input_builder import (
    build_classifier_payload,
)

from jobly.market.us_scope import (
    classify_us_job,
)


def _max_attempts() -> int:
    return get_settings().ai_max_attempts


def recover_stale_jobs(
    conn,
):

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_status =
                    CASE

                        WHEN
                            classification_attempts >= %s

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

                AND classification_started_at <
                    NOW()
                    - INTERVAL '15 minutes'
            """,
            (
                _max_attempts(),
            ),
        )


    conn.commit()


def count_pending_fresh_jobs(
    conn,
):

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT COUNT(*)

            FROM jobs

            WHERE
                active = TRUE

                AND posted_at IS NOT NULL

                AND posted_at >=
                    NOW()
                    - INTERVAL '48 hours'

                AND content_hash
                    IS NOT NULL

                AND classification_status =
                    'pending'

                AND classification_attempts
                    < %s
            """,
            (
                _max_attempts(),
            ),
        )


        return (
            cur.fetchone()[0]
        )


def claim_next_job(
    conn,
):

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

                AND posted_at
                    IS NOT NULL

                AND posted_at >=
                    NOW()
                    - INTERVAL '48 hours'

                AND content_hash
                    IS NOT NULL

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
                _max_attempts(),
            ),
        )


        job = (
            cur.fetchone()
        )


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

                classification_error =
                    NULL

            WHERE id = %s
            """,
            (
                job["id"],
            ),
        )


    conn.commit()


    return job


def save_market_decision(
    conn,
    job: dict,
    eligible: bool,
    reason: str,
):

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                is_us_job = %s,

                us_location_reason =
                    %s

            WHERE
                id = %s

                AND content_hash = %s
            """,
            (
                eligible,
                reason,

                job["id"],
                job["content_hash"],
            ),
        )


    conn.commit()


def skip_non_us_job(
    conn,
    job: dict,
    reason: str,
):

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                is_us_job = FALSE,

                us_location_reason =
                    %s,

                classification_status =
                    'skipped_non_us',

                classification_started_at =
                    NULL,

                classification_error =
                    NULL

            WHERE
                id = %s

                AND content_hash =
                    %s
            """,
            (
                reason,

                job["id"],

                job["content_hash"],
            ),
        )


    conn.commit()


def increment_ai_attempt(
    conn,
    job_id: int,
):

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs

            SET
                classification_attempts =
                    classification_attempts + 1

            WHERE id = %s
            """,
            (
                job_id,
            ),
        )


    conn.commit()


def reset_changed_job(
    conn,
    job_id: int,
):

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

                years_experience_min =
                    %s,

                years_experience_max =
                    %s,

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
                    NULL,

                is_us_job = TRUE

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

                get_settings().ai_classification_version,

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
            "STALE RESULT | job=%s",
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

                AND content_hash =
                    %s
            """,
            (
                _max_attempts(),

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

    # ========================================================
    # U.S. market gate
    # ========================================================

    decision = (
        classify_us_job(
            provider=(
                job["provider"]
            ),

            location=(
                job["location"]
            ),

            raw=(
                job["raw_payload"]
            ),
        )
    )


    save_market_decision(
        conn,
        job,
        decision.eligible,
        decision.reason,
    )


    if not decision.eligible:

        logging.info(
            (
                "SKIP NON-US | "
                "id=%s | "
                "location=%s | "
                "reason=%s"
            ),

            job["id"],
            job["location"],
            decision.reason,
        )


        skip_non_us_job(
            conn,
            job,
            decision.reason,
        )


        return "skipped_non_us"


    # ========================================================
    # U.S. job — now AI processing can start
    # ========================================================

    increment_ai_attempt(
        conn,
        job["id"],
    )


    payload = (
        build_classifier_payload(
            job
        )
    )


    logging.info(
        (
            "CLASSIFY US | "
            "id=%s | "
            "provider=%s | "
            "posted_at=%s | "
            "location=%s | "
            "title=%s"
        ),

        job["id"],
        job["provider"],
        job["posted_at"],
        job["location"],
        job["title"],
    )


    classification = (
        classify_job(
            payload
        )
    )


    saved = (
        save_success(
            conn,
            job,
            classification,
        )
    )


    if not saved:
        return "stale"


    logging.info(
        (
            "READY US | "
            "id=%s | "
            "family=%s | "
            "seniority=%s | "
            "confidence=%.2f"
        ),

        job["id"],

        classification.job_family,

        classification.seniority,

        classification.confidence,
    )


    return "ready"


def main():

    parser = (
        argparse.ArgumentParser()
    )


    parser.add_argument(
        "--limit",

        type=int,

        default=10,

        help=(
            "Maximum number of U.S. "
            "jobs sent to AI"
        ),
    )


    args = (
        parser.parse_args()
    )


    if args.limit < 1:

        raise ValueError(
            "--limit must be at least 1"
        )


    ai_processed = 0

    successful = 0

    failed = 0

    skipped_non_us = 0


    with get_connection() as conn:

        recover_stale_jobs(
            conn
        )


        pending = (
            count_pending_fresh_jobs(
                conn
            )
        )


        print(
            "Fresh pending candidates:",
            pending,
        )


        while (
            ai_processed
            < args.limit
        ):

            job = (
                claim_next_job(
                    conn
                )
            )


            if job is None:
                break


            try:

                result = (
                    process_job(
                        conn,
                        job,
                    )
                )


                if (
                    result ==
                    "skipped_non_us"
                ):

                    skipped_non_us += 1

                    continue


                if result == "ready":

                    ai_processed += 1

                    successful += 1


                elif result == "stale":

                    ai_processed += 1


            except Exception as exc:

                ai_processed += 1

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


    logging.info(
        (
            "WORKER COMPLETE | "
            "ai_processed=%s | "
            "successful=%s | "
            "failed=%s | "
            "skipped_non_us=%s"
        ),

        ai_processed,
        successful,
        failed,
        skipped_non_us,
    )


    print()

    print(
        "AI processed:",
        ai_processed,
    )

    print(
        "Successful:",
        successful,
    )

    print(
        "Failed:",
        failed,
    )

    print(
        "Skipped non-US:",
        skipped_non_us,
    )


if __name__ == "__main__":
    main()
