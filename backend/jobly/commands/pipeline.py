import argparse
import logging
import subprocess
import sys
import time

from jobly.config import (
    get_settings,
)
from jobly.db.connection import (
    get_connection,
)
from jobly.logging_config import (
    configure_logging,
)


logger = logging.getLogger(
    __name__
)


def _run(
    command: list[str],
    name: str,
) -> None:

    logger.info(
        "pipeline_stage_start stage=%s",
        name,
    )

    started = (
        time.monotonic()
    )


    result = subprocess.run(
        command,
        check=False,
    )


    duration = (
        time.monotonic()
        - started
    )


    if result.returncode:

        logger.error(
            (
                "pipeline_stage_failed "
                "stage=%s "
                "status=failed "
                "exit_code=%s "
                "duration=%.2f"
            ),
            name,
            result.returncode,
            duration,
        )

        raise SystemExit(
            result.returncode
        )


    logger.info(
        (
            "pipeline_stage_complete "
            "stage=%s "
            "status=success "
            "duration=%.2f"
        ),
        name,
        duration,
    )


def log_pipeline_summary() -> None:

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)
                FROM sources
                WHERE status = 'active'
                """
            )

            active_sources = (
                cur.fetchone()[0]
            )


            cur.execute(
                """
                SELECT COUNT(*)
                FROM sources
                WHERE status = 'invalid'
                """
            )

            invalid_sources = (
                cur.fetchone()[0]
            )


            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE active = TRUE
                """
            )

            active_jobs = (
                cur.fetchone()[0]
            )


            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE
                    active = TRUE
                    AND classification_status =
                        'pending'
                """
            )

            pending_jobs = (
                cur.fetchone()[0]
            )


            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE
                    active = TRUE
                    AND classification_status =
                        'ready'
                """
            )

            ready_jobs = (
                cur.fetchone()[0]
            )


            cur.execute(
                """
                SELECT COUNT(*)
                FROM public_jobs
                """
            )

            public_jobs = (
                cur.fetchone()[0]
            )


    logger.info(
        (
            "pipeline_summary "
            "active_sources=%s "
            "invalid_sources=%s "
            "active_jobs=%s "
            "pending_jobs=%s "
            "ready_jobs=%s "
            "public_jobs=%s"
        ),
        active_sources,
        invalid_sources,
        active_jobs,
        pending_jobs,
        ready_jobs,
        public_jobs,
    )


def main() -> None:

    settings = get_settings()


    parser = argparse.ArgumentParser(
        description=(
            "Run the complete Jobly ingestion "
            "pipeline once."
        )
    )


    parser.add_argument(
        "--source-target",
        type=int,
        default=(
            settings.crawl_source_limit
        ),
        help=(
            "Override CRAWL_SOURCE_LIMIT."
        ),
    )


    parser.add_argument(
        "--enrichment-limit",
        type=int,
        default=500,
    )


    args = parser.parse_args()


    if args.source_target is None:

        parser.error(
            (
                "Source target is required. "
                "Set CRAWL_SOURCE_LIMIT "
                "or pass --source-target."
            )
        )


    if args.source_target < 1:

        parser.error(
            "--source-target must be at least 1"
        )


    if args.enrichment_limit < 1:

        parser.error(
            "--enrichment-limit must "
            "be at least 1"
        )


    configure_logging()


    started = (
        time.monotonic()
    )


    logger.info(
        (
            "pipeline_start "
            "source_target=%s "
            "enrichment_limit=%s"
        ),
        args.source_target,
        args.enrichment_limit,
    )


    # ========================================================
    # 1. Ensure database schema is current
    # ========================================================

    _run(
        [
            sys.executable,
            "-m",
            "jobly.commands.migrate",
        ],
        "migrate",
    )


    # ========================================================
    # 2. Ensure enough validated sources exist
    # ========================================================

    _run(
        [
            sys.executable,
            "-m",
            "jobly.commands.sync_sources",

            "--target",
            str(
                args.source_target
            ),
        ],
        "sync_sources",
    )


    # ========================================================
    # 3. Crawl exactly the requested source set
    # ========================================================

    _run(
        [
            sys.executable,
            "-m",
            "jobly.commands.crawl",

            "--source-limit",
            str(
                args.source_target
            ),
        ],
        "crawl",
    )


    # ========================================================
    # 4. Enrich new / changed fresh U.S. jobs
    # ========================================================

    _run(
        [
            sys.executable,
            "-m",
            "jobly.commands.enrich",

            "--limit",
            str(
                args.enrichment_limit
            ),
        ],
        "enrich",
    )


    # ========================================================
    # 5. Final state summary
    # ========================================================

    log_pipeline_summary()


    logger.info(
        (
            "pipeline_complete "
            "status=success "
            "duration=%.2f"
        ),
        (
            time.monotonic()
            - started
        ),
    )


if __name__ == "__main__":
    main()