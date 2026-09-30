import csv
import logging
import os
import subprocess
import sys
import time

from datetime import datetime, timezone
from pathlib import Path

from jobly.db.connection import get_connection


# ============================================================
# Configuration
# ============================================================

SOAK_HOURS = 48

CRAWL_INTERVAL_HOURS = 3

AI_LIMIT_PER_CYCLE = 500


# ============================================================
# Paths
# ============================================================

REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND_ROOT = REPO_ROOT / "backend"

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
# Subprocess environment
# ============================================================

def build_subprocess_env() -> dict:
    """
    Ensure child Python processes can import the installed-style `jobly` package.
    """

    env = os.environ.copy()

    existing_pythonpath = (
        env.get(
            "PYTHONPATH",
            "",
        )
    )

    backend_path = str(
        BACKEND_ROOT
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
# Commands
# ============================================================

def run_command(
    name: str,
    command: list[str],
) -> bool:

    logging.info(
        "START | %s",
        name,
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
            result.returncode == 0
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
            # Removed jobs
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
            # Fresh jobs
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
            # Sources currently failing
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
            # Highest source failure count
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
            # Crawl activity over last 4 hours
            # ------------------------------------------------

            cur.execute(
                """
                SELECT

                    COUNT(*)
                    FILTER (
                        WHERE
                            status = 'success'
                    ),

                    COUNT(*)
                    FILTER (
                        WHERE
                            status = 'failed'
                    )

                FROM crawl_runs

                WHERE
                    started_at >=
                        NOW()
                        - INTERVAL '4 hours'
                """
            )

            crawl_row = (
                cur.fetchone()
            )

            crawl_successes = (
                crawl_row[0]
            )

            crawl_failures = (
                crawl_row[1]
            )


    return {
        "timestamp": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "active_sources":
            active_sources,

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

        "fresh_ready":
            fresh_ready,

        "fresh_failed":
            fresh_failed,

        "public_jobs":
            public_jobs,

        "failing_sources":
            failing_sources,

        "max_source_failures":
            max_source_failures,

        "crawl_successes":
            crawl_successes,

        "crawl_failures":
            crawl_failures,
    }


# ============================================================
# Save metrics
# ============================================================

def save_metrics(
    cycle: int,
    metrics: dict,
):

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

    logging.info(
        (
            "METRICS | "
            "cycle=%s | "
            "sources=%s | "
            "jobs=%s | "
            "active=%s | "
            "removed=%s | "
            "fresh=%s | "
            "ready=%s | "
            "pending=%s | "
            "ai_failed=%s | "
            "public=%s | "
            "source_failures=%s | "
            "crawl_success=%s | "
            "crawl_failed=%s"
        ),

        cycle,

        metrics[
            "active_sources"
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
            "fresh_failed"
        ],

        metrics[
            "public_jobs"
        ],

        metrics[
            "failing_sources"
        ],

        metrics[
            "crawl_successes"
        ],

        metrics[
            "crawl_failures"
        ],
    )


# ============================================================
# One complete cycle
# ============================================================

def run_cycle(
    cycle: int,
):

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


    # --------------------------------------------------------
    # Crawl first 50 sources
    # --------------------------------------------------------

    crawl_ok = (
        run_command(
            "crawler",

            [
                sys.executable,
                "-m",
                "jobly.commands.crawl",
            ],
        )
    )


    # --------------------------------------------------------
    # Run AI after crawler
    # --------------------------------------------------------

    ai_ok = (
        run_command(
            "AI enrichment",

            [
                sys.executable,
                "-m",
                "jobly.commands.enrich",

                "--limit",

                str(
                    AI_LIMIT_PER_CYCLE
                ),
            ],
        )
    )


    # --------------------------------------------------------
    # Record DB state
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


    logging.info(
        (
            "CYCLE %s COMPLETE | "
            "crawler=%s | "
            "ai=%s"
        ),

        cycle,

        (
            "ok"
            if crawl_ok
            else "failed"
        ),

        (
            "ok"
            if ai_ok
            else "failed"
        ),
    )


# ============================================================
# Main
# ============================================================

def main():

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
        "JOBLY LOCAL SOAK START"
    )

    logging.info(
        "Repository root: %s",
        REPO_ROOT,
    )

    logging.info(
        "Duration: %s hours",
        SOAK_HOURS,
    )

    logging.info(
        "Interval: %s hours",
        CRAWL_INTERVAL_HOURS,
    )

    logging.info(
        "AI limit/cycle: %s",
        AI_LIMIT_PER_CYCLE,
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

            cycle_started = (
                time.monotonic()
            )


            run_cycle(
                cycle
            )


            cycle += 1


            if (
                time.monotonic()
                >= soak_ends
            ):
                break


            next_cycle = (
                cycle_started
                + interval_seconds
            )


            sleep_seconds = max(
                0,
                next_cycle
                - time.monotonic(),
            )


            remaining_seconds = (
                soak_ends
                - time.monotonic()
            )


            sleep_seconds = min(
                sleep_seconds,
                remaining_seconds,
            )


            logging.info(
                (
                    "Sleeping %.1f minutes "
                    "until next cycle"
                ),

                sleep_seconds
                / 60,
            )


            time.sleep(
                sleep_seconds
            )


    except KeyboardInterrupt:

        logging.warning(
            "SOAK STOPPED MANUALLY"
        )


    logging.info(
        "JOBLY LOCAL SOAK COMPLETE"
    )


if __name__ == "__main__":
    main()
