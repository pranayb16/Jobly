import csv
import logging
import os
import subprocess
import sys
import time

from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# Repository paths
# ============================================================

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND_ROOT = (
    REPO_ROOT
    / "backend"
)


# ============================================================
# Make backend/jobly importable
# ============================================================

backend_path = str(
    BACKEND_ROOT
)

if backend_path not in sys.path:
    sys.path.insert(
        0,
        backend_path,
    )


# Import after backend is added to sys.path
from jobly.db.connection import get_connection  # noqa: E402


# ============================================================
# Load .env
# ============================================================

load_dotenv(
    REPO_ROOT / ".env"
)


# ============================================================
# Configuration
# ============================================================

# Total amount of time this soak test should run.
#
# Default:
# 168 hours = 7 days
SOAK_HOURS = int(
    os.getenv(
        "SOAK_HOURS",
        "168",
    )
)


# How often to start the complete pipeline.
#
# 8 hours = 3 runs/day
CRAWL_INTERVAL_HOURS = int(
    os.getenv(
        "CRAWL_INTERVAL_HOURS",
        "8",
    )
)


# Maximum number of fresh U.S. jobs
# sent to Gemini each pipeline cycle.
AI_LIMIT_PER_CYCLE = int(
    os.getenv(
        "AI_LIMIT_PER_CYCLE",
        "500",
    )
)


# Used only for logging.
#
# The actual source target is consumed by
# jobly.commands.pipeline from .env.
CRAWL_SOURCE_LIMIT = int(
    os.getenv(
        "CRAWL_SOURCE_LIMIT",
        "50",
    )
)


# ============================================================
# Log paths
# ============================================================

LOG_DIR = (
    REPO_ROOT
    / "logs"
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SOAK_LOG = (
    LOG_DIR
    / "soak.log"
)


METRICS_FILE = (
    LOG_DIR
    / "soak_metrics.csv"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),

    handlers=[
        logging.FileHandler(
            SOAK_LOG,
            encoding="utf-8",
        ),

        logging.StreamHandler(
            sys.stdout
        ),
    ],
)


# ============================================================
# Child-process environment
# ============================================================

def build_subprocess_env() -> dict:
    """
    Build the environment passed to pipeline subprocesses.

    This makes sure:
    - .env variables are available
    - backend/jobly can be imported
    """

    env = (
        os.environ.copy()
    )


    existing_pythonpath = (
        env.get(
            "PYTHONPATH",
            "",
        )
    )


    if existing_pythonpath:

        env["PYTHONPATH"] = (
            backend_path
            + os.pathsep
            + existing_pythonpath
        )

    else:

        env["PYTHONPATH"] = (
            backend_path
        )


    return env


# ============================================================
# Run external command
# ============================================================

def run_command(
    name: str,
    command: list[str],
) -> bool:
    """
    Run one subprocess and wait for it to finish.

    Returns:
        True  -> command succeeded
        False -> command failed

    The soak runner will not start another cycle while this
    command is still running.
    """

    logging.info(
        "START | %s",
        name,
    )

    logging.info(
        "COMMAND | %s",
        " ".join(command),
    )

    logging.info(
        "WORKING DIRECTORY | %s",
        REPO_ROOT,
    )


    started = (
        time.monotonic()
    )


    try:

        result = subprocess.run(
            command,

            cwd=str(
                REPO_ROOT
            ),

            env=(
                build_subprocess_env()
            ),

            check=False,

            text=True,
        )


        duration = (
            time.monotonic()
            - started
        )


        if (
            result.returncode
            == 0
        ):

            logging.info(
                (
                    "SUCCESS | %s | "
                    "duration=%.1fs"
                ),

                name,
                duration,
            )

            return True


        logging.error(
            (
                "FAILED | %s | "
                "exit_code=%s | "
                "duration=%.1fs"
            ),

            name,
            result.returncode,
            duration,
        )

        return False


    except Exception:

        logging.exception(
            "EXCEPTION | %s",
            name,
        )

        return False


# ============================================================
# Database metrics
# ============================================================

def collect_metrics() -> dict:
    """
    Collect useful state after every complete pipeline cycle.
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            # ------------------------------------------------
            # Active sources
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Invalid sources
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Total jobs
            # ------------------------------------------------

            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                """
            )

            total_jobs = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Active jobs
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Removed / inactive jobs
            # ------------------------------------------------

            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE active = FALSE
                """
            )

            removed_jobs = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh jobs: last 48 hours
            # ------------------------------------------------

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
                """
            )

            fresh_jobs = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh pending AI jobs
            # ------------------------------------------------

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

                    AND classification_status =
                        'pending'
                """
            )

            fresh_pending = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh processing AI jobs
            # ------------------------------------------------

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

                    AND classification_status =
                        'processing'
                """
            )

            fresh_processing = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh ready AI jobs
            # ------------------------------------------------

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

                    AND classification_status =
                        'ready'
                """
            )

            fresh_ready = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh AI failures
            # ------------------------------------------------

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

                    AND classification_status =
                        'failed'
                """
            )

            fresh_failed = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Fresh non-US jobs skipped before Gemini
            # ------------------------------------------------

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

                    AND classification_status =
                        'skipped_non_us'
                """
            )

            fresh_non_us = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Public jobs
            # ------------------------------------------------

            cur.execute(
                """
                SELECT COUNT(*)
                FROM public_jobs
                """
            )

            public_jobs = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Sources with at least one crawl failure
            # ------------------------------------------------

            cur.execute(
                """
                SELECT COUNT(*)

                FROM sources

                WHERE
                    consecutive_failures > 0
                """
            )

            failing_sources = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Highest consecutive failure count
            # ------------------------------------------------

            cur.execute(
                """
                SELECT
                    COALESCE(
                        MAX(
                            consecutive_failures
                        ),
                        0
                    )

                FROM sources
                """
            )

            max_source_failures = (
                cur.fetchone()[0]
            )


            # ------------------------------------------------
            # Total crawl runs
            # ------------------------------------------------

            cur.execute(
                """
                SELECT
                    COUNT(*)
                    FILTER (
                        WHERE status = 'success'
                    ),

                    COUNT(*)
                    FILTER (
                        WHERE status = 'failed'
                    )

                FROM crawl_runs
                """
            )

            crawl_row = (
                cur.fetchone()
            )

            total_crawl_successes = (
                crawl_row[0]
            )

            total_crawl_failures = (
                crawl_row[1]
            )


    return {
        "timestamp": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "source_target":
            CRAWL_SOURCE_LIMIT,

        "active_sources":
            active_sources,

        "invalid_sources":
            invalid_sources,

        "total_jobs":
            total_jobs,

        "active_jobs":
            active_jobs,

        "removed_jobs":
            removed_jobs,

        "fresh_jobs":
            fresh_jobs,

        "fresh_pending":
            fresh_pending,

        "fresh_processing":
            fresh_processing,

        "fresh_ready":
            fresh_ready,

        "fresh_failed":
            fresh_failed,

        "fresh_non_us":
            fresh_non_us,

        "public_jobs":
            public_jobs,

        "failing_sources":
            failing_sources,

        "max_source_failures":
            max_source_failures,

        "total_crawl_successes":
            total_crawl_successes,

        "total_crawl_failures":
            total_crawl_failures,
    }


# ============================================================
# Save metrics
# ============================================================

def save_metrics(
    cycle: int,
    metrics: dict,
):
    """
    Append one row to logs/soak_metrics.csv.
    """

    row = {
        "cycle": cycle,
        **metrics,
    }


    file_exists = (
        METRICS_FILE.exists()
    )


    with METRICS_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = (
            csv.DictWriter(
                file,
                fieldnames=row.keys(),
            )
        )


        if not file_exists:

            writer.writeheader()


        writer.writerow(
            row
        )


# ============================================================
# Log metrics
# ============================================================

def log_metrics(
    cycle: int,
    metrics: dict,
):
    """
    Print the most important system state after each cycle.
    """

    logging.info(
        (
            "METRICS | "
            "cycle=%s | "
            "source_target=%s | "
            "active_sources=%s | "
            "invalid_sources=%s | "
            "total_jobs=%s | "
            "active_jobs=%s | "
            "removed_jobs=%s | "
            "fresh_jobs=%s | "
            "ready=%s | "
            "pending=%s | "
            "processing=%s | "
            "ai_failed=%s | "
            "non_us=%s | "
            "public=%s | "
            "failing_sources=%s | "
            "max_source_failures=%s | "
            "crawl_success_total=%s | "
            "crawl_failed_total=%s"
        ),

        cycle,

        metrics[
            "source_target"
        ],

        metrics[
            "active_sources"
        ],

        metrics[
            "invalid_sources"
        ],

        metrics[
            "total_jobs"
        ],

        metrics[
            "active_jobs"
        ],

        metrics[
            "removed_jobs"
        ],

        metrics[
            "fresh_jobs"
        ],

        metrics[
            "fresh_ready"
        ],

        metrics[
            "fresh_pending"
        ],

        metrics[
            "fresh_processing"
        ],

        metrics[
            "fresh_failed"
        ],

        metrics[
            "fresh_non_us"
        ],

        metrics[
            "public_jobs"
        ],

        metrics[
            "failing_sources"
        ],

        metrics[
            "max_source_failures"
        ],

        metrics[
            "total_crawl_successes"
        ],

        metrics[
            "total_crawl_failures"
        ],
    )


# ============================================================
# One complete pipeline cycle
# ============================================================

def run_cycle(
    cycle: int,
):
    """
    Run one FULL Jobly pipeline.

    The pipeline is responsible for:

        1. database migrations
        2. checking source target
        3. loading additional CSV sources if needed
        4. validating those new ATS sources
        5. inserting usable sources into PostgreSQL
        6. crawling CRAWL_SOURCE_LIMIT sources
        7. normalizing and storing jobs
        8. marking new/changed jobs pending
        9. U.S. eligibility filtering
       10. Gemini enrichment
       11. publishing ready jobs through public_jobs

    dev_soak.py does NOT implement those steps itself.

    Its only responsibility is:
        run pipeline -> metrics -> sleep -> repeat.
    """

    logging.info(
        "========================================"
    )

    logging.info(
        "CYCLE %s START",
        cycle,
    )

    logging.info(
        "========================================"
    )


    cycle_started = (
        time.monotonic()
    )


    # --------------------------------------------------------
    # Complete Jobly pipeline
    # --------------------------------------------------------

    pipeline_ok = (
        run_command(
            "pipeline",

            [
                sys.executable,

                "-m",
                "jobly.commands.pipeline",

                "--enrichment-limit",
                str(
                    AI_LIMIT_PER_CYCLE
                ),
            ],
        )
    )


    # --------------------------------------------------------
    # Collect DB metrics regardless of pipeline result
    # --------------------------------------------------------

    try:

        metrics = (
            collect_metrics()
        )


        save_metrics(
            cycle,
            metrics,
        )


        log_metrics(
            cycle,
            metrics,
        )


    except Exception:

        logging.exception(
            "FAILED TO COLLECT METRICS"
        )


    # --------------------------------------------------------
    # Final cycle status
    # --------------------------------------------------------

    duration = (
        time.monotonic()
        - cycle_started
    )


    logging.info(
        (
            "CYCLE %s COMPLETE | "
            "pipeline=%s | "
            "duration=%.1fs"
        ),

        cycle,

        (
            "ok"
            if pipeline_ok
            else "failed"
        ),

        duration,
    )


# ============================================================
# Main soak loop
# ============================================================

def main():

    if SOAK_HOURS < 1:

        raise ValueError(
            "SOAK_HOURS must be at least 1"
        )


    if CRAWL_INTERVAL_HOURS < 1:

        raise ValueError(
            "CRAWL_INTERVAL_HOURS must be at least 1"
        )


    if AI_LIMIT_PER_CYCLE < 1:

        raise ValueError(
            "AI_LIMIT_PER_CYCLE must be at least 1"
        )


    if CRAWL_SOURCE_LIMIT < 1:

        raise ValueError(
            "CRAWL_SOURCE_LIMIT must be at least 1"
        )


    duration_seconds = (
        SOAK_HOURS
        * 60
        * 60
    )


    interval_seconds = (
        CRAWL_INTERVAL_HOURS
        * 60
        * 60
    )


    soak_started = (
        time.monotonic()
    )


    soak_ends = (
        soak_started
        + duration_seconds
    )


    logging.info(
        "========================================"
    )

    logging.info(
        "JOBLY LOCAL SOAK START"
    )

    logging.info(
        "========================================"
    )


    logging.info(
        "Repository root: %s",
        REPO_ROOT,
    )


    logging.info(
        "Backend root: %s",
        BACKEND_ROOT,
    )


    logging.info(
        "Duration: %s hours",
        SOAK_HOURS,
    )


    logging.info(
        "Pipeline interval: %s hours",
        CRAWL_INTERVAL_HOURS,
    )


    logging.info(
        "Source target: %s",
        CRAWL_SOURCE_LIMIT,
    )


    logging.info(
        "AI limit/cycle: %s",
        AI_LIMIT_PER_CYCLE,
    )


    logging.info(
        "Log file: %s",
        SOAK_LOG,
    )


    logging.info(
        "Metrics file: %s",
        METRICS_FILE,
    )


    cycle = 1


    try:

        while (
            time.monotonic()
            < soak_ends
        ):

            # ------------------------------------------------
            # Remember when this cycle was scheduled from
            # ------------------------------------------------

            cycle_started = (
                time.monotonic()
            )


            # ------------------------------------------------
            # Run full pipeline
            # ------------------------------------------------

            run_cycle(
                cycle
            )


            cycle += 1


            # ------------------------------------------------
            # Stop if soak duration has expired
            # ------------------------------------------------

            if (
                time.monotonic()
                >= soak_ends
            ):

                break


            # ------------------------------------------------
            # Target next run based on previous cycle START
            #
            # Example:
            #
            # cycle starts 8:00
            # next target 16:00
            #
            # If crawl takes 2 hours:
            # sleep ~6 hours
            #
            # If crawl takes >8 hours:
            # sleep = 0 and next cycle starts immediately.
            #
            # This prevents overlapping pipelines.
            # ------------------------------------------------

            next_cycle = (
                cycle_started
                + interval_seconds
            )


            sleep_seconds = max(
                0,
                next_cycle
                - time.monotonic(),
            )


            # ------------------------------------------------
            # Do not sleep beyond the total soak duration
            # ------------------------------------------------

            remaining_seconds = (
                soak_ends
                - time.monotonic()
            )


            sleep_seconds = min(
                sleep_seconds,
                remaining_seconds,
            )


            if (
                sleep_seconds
                > 0
            ):

                logging.info(
                    (
                        "Sleeping %.1f minutes "
                        "until next pipeline cycle"
                    ),

                    sleep_seconds
                    / 60,
                )


                time.sleep(
                    sleep_seconds
                )

            else:

                logging.warning(
                    (
                        "Previous cycle consumed "
                        "the full interval; "
                        "starting next cycle immediately"
                    )
                )


    except KeyboardInterrupt:

        logging.warning(
            "SOAK STOPPED MANUALLY"
        )


    total_duration = (
        time.monotonic()
        - soak_started
    )


    logging.info(
        "========================================"
    )

    logging.info(
        (
            "JOBLY LOCAL SOAK COMPLETE | "
            "duration=%.1f hours"
        ),

        total_duration
        / 60
        / 60,
    )

    logging.info(
        "========================================"
    )


if __name__ == "__main__":
    main()