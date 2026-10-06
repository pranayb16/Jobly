from __future__ import annotations

import argparse

from jobly.config import get_settings
from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging


def enqueue_bootstrap(
    conn,
    schema_version: str,
) -> int:
    """
    Queue all current active jobs that do not have enrichment
    for their current content hash and requested schema version.

    Existing completed/failed queue records are reopened because
    they may have been processed under an older enrichment schema.

    Existing pending/processing work is left untouched.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO enrichment_queue (
                job_id,
                content_hash,
                schema_version,
                priority,
                reason
            )

            SELECT
                j.id,
                j.content_hash,
                %s,
                3,
                'bootstrap'

            FROM jobs AS j

            WHERE j.active = TRUE

              AND j.content_hash IS NOT NULL

              AND j.enrichment_eligibility = 'eligible'

              AND (
                  j.posted_at IS NULL
                  OR j.posted_at >= NOW() - INTERVAL '7 days'
              )

              -- Do not repeatedly enrich jobs already known to
              -- be outside the U.S. market.
              AND j.is_us_job IS DISTINCT FROM FALSE

              -- Only queue jobs that do not already have the
              -- requested current enrichment.
              AND NOT EXISTS (
                  SELECT 1

                  FROM job_enrichments AS e

                  WHERE e.job_id = j.id

                    AND e.content_hash =
                        j.content_hash

                    AND e.schema_version = %s
              )

            ON CONFLICT (
                job_id,
                content_hash,
                schema_version
            )

            DO UPDATE SET

                status = 'pending',

                priority = 3,

                reason = 'bootstrap',

                attempts = 0,

                started_at = NULL,

                completed_at = NULL,

                last_error = NULL

                , error_class = NULL

                , retryable = NULL

                , next_attempt_at = NULL

            WHERE enrichment_queue.status
                  IN (
                      'completed',
                      'failed'
                  )
            """,
            (
                schema_version,
                schema_version,
            ),
        )

        queued = cur.rowcount

    conn.commit()

    return queued


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Idempotently queue current jobs "
            "that lack current enrichment."
        )
    )

    parser.add_argument(
        "--schema-version",
        default=(
            get_settings()
            .ai_classification_version
        ),
    )

    args = parser.parse_args()

    configure_logging()

    with get_connection() as conn:
        queued = enqueue_bootstrap(
            conn,
            args.schema_version,
        )

    print(
        "Bootstrap enrichment queue complete | "
        f"schema={args.schema_version} | "
        f"queued_or_reopened={queued}"
    )


if __name__ == "__main__":
    main()
