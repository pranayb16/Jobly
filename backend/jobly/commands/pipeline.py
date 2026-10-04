from __future__ import annotations

import argparse
import logging

from pathlib import Path


from jobly.commands.migrate import (
    DEFAULT_MIGRATIONS_DIR,
    run_migrations,
)

from jobly.config import (
    get_settings,
)

from jobly.crawling.worker import (
    run_crawl,
)

from jobly.db.connection import (
    get_connection,
)

from jobly.enrichment.worker import (
    run_enrichment,
)

from jobly.intelligence.hiring_stats import (
    refresh_hiring_stats,
)

from jobly.intelligence.snapshots import (
    build_snapshots,
)

from jobly.pipeline.repository import (
    create_pipeline_run,
    ensure_pipeline_run_table,
    finish_pipeline_run,
)

from jobly.sources.manager import (
    ensure_source_target,
)

from jobly.logging_config import (
    configure_logging,
    enable_pipeline_database_logging,
)

from jobly.observability.context import (
    set_pipeline_run_id,
    set_pipeline_stage,
)

from jobly.observability.repository import (
    finish_stage,
    start_stage,
)


logger = logging.getLogger(
    __name__
)


def determine_pipeline_status(
    *,
    crawl_failures: int,
    enrichment_failures: int,
    enrichment_backlog: int,
) -> str:

    del enrichment_backlog


    if (
        crawl_failures
        or enrichment_failures
    ):
        return "partial_success"


    return "success"


def run_pipeline(
    *,
    source_target: int,
    source_limit: int | None,
    enrichment_limit: int,
    migrations_dir: Path = (
        DEFAULT_MIGRATIONS_DIR
    ),
) -> int:

    with get_connection() as conn:

        ensure_pipeline_run_table(
            conn
        )


        pipeline_run_id = (
            create_pipeline_run(
                conn,
                source_target,
            )
        )

        set_pipeline_run_id(
            pipeline_run_id
        )


    metrics: dict[str, int] = {}


    try:

        # -----------------------------------------------------
        # 1. Migrations
        # -----------------------------------------------------

        run_migrations(
            migrations_dir
        )

        enable_pipeline_database_logging()


        # -----------------------------------------------------
        # 2. Source target
        # -----------------------------------------------------

        source_summary = (
            ensure_source_target(
                source_target
            )
        )


        # -----------------------------------------------------
        # 3. Crawl
        # -----------------------------------------------------

        crawl_summary = run_crawl(
            source_limit,
            pipeline_run_id,
        )


        # -----------------------------------------------------
        # 4. AI enrichment
        #
        # Queue ordering:
        #
        # 1 = new_job
        # 2 = changed_job
        # 3 = bootstrap
        #
        # enrichment_limit is the total maximum actual
        # classifications during this pipeline run.
        # -----------------------------------------------------

        enrichment_summary = (
            run_enrichment(
                enrichment_limit
            )
        )


        # -----------------------------------------------------
        # 5. Existing daily snapshots
        #
        # Retained for current compatibility / internal
        # historical logging.
        #
        # Hiring statistics below DO NOT use snapshots.
        # -----------------------------------------------------

        snapshot_summary = (
            build_snapshots()
        )


        # -----------------------------------------------------
        # 6. Deterministic hiring statistics
        #
        # This is intentionally the final data-product stage.
        #
        # It reads current source-of-truth job rows and
        # recalculates the company_hiring_stats table.
        #
        # It does NOT depend on AI enrichment output.
        # -----------------------------------------------------

        hiring_stats_summary = (
            refresh_hiring_stats()
        )


        # -----------------------------------------------------
        # 7. Metrics
        # -----------------------------------------------------

        metrics = {

            "sources_attempted":
                crawl_summary.source_count,

            "sources_successful":
                crawl_summary.successful_sources,

            "sources_failed":
                crawl_summary.failed_sources,

            "jobs_seen":
                crawl_summary.job_count,

            "jobs_new":
                crawl_summary.jobs_new,

            "jobs_changed":
                crawl_summary.jobs_changed,

            "jobs_removed":
                crawl_summary.jobs_removed,


            "enrichments_processed":
                enrichment_summary.processed,

            "enrichments_completed":
                enrichment_summary.completed,

            "enrichments_failed":
                enrichment_summary.failed,

            "enrichments_skipped_non_us":
                enrichment_summary.skipped_non_us,

            "enrichment_backlog":
                enrichment_summary.backlog,


            "gemini_input_tokens":
                enrichment_summary.input_tokens,

            "gemini_output_tokens":
                enrichment_summary.output_tokens,

            "gemini_thought_tokens":
                enrichment_summary.thought_tokens,

            "gemini_cached_tokens":
                enrichment_summary.cached_tokens,

            "gemini_total_tokens":
                enrichment_summary.total_tokens,


            "snapshots_created":
                snapshot_summary.snapshots_created,


            "company_stats_refreshed":
                hiring_stats_summary
                .companies_refreshed,

            "company_stats_publishable":
                hiring_stats_summary
                .publishable_companies,

            "company_stats_unpublishable":
                hiring_stats_summary
                .unpublishable_companies,
        }


        status = determine_pipeline_status(

            crawl_failures=(
                crawl_summary.failed_sources
            ),

            enrichment_failures=(
                enrichment_summary.failed
            ),

            enrichment_backlog=(
                enrichment_summary.backlog
            ),
        )


        with get_connection() as conn:

            finish_pipeline_run(
                conn,
                pipeline_run_id,
                status,
                metrics,
            )


        logger.info(
            "pipeline_complete "
            "pipeline_run_id=%s "
            "status=%s "
            "source_sync=%s "
            "metrics=%s",
            pipeline_run_id,
            status,
            source_summary,
            metrics,
        )


        print(
            "Pipeline complete | "
            f"pipeline_run_id="
            f"{pipeline_run_id} | "
            f"status={status}"
        )


        print(
            "Crawl | "
            f"sources="
            f"{crawl_summary.source_count} | "
            f"new="
            f"{crawl_summary.jobs_new} | "
            f"changed="
            f"{crawl_summary.jobs_changed} | "
            f"removed="
            f"{crawl_summary.jobs_removed}"
        )


        print(
            "Enrichment | "
            f"processed="
            f"{enrichment_summary.processed} | "
            f"ai_calls="
            f"{enrichment_summary.ai_calls} | "
            f"completed="
            f"{enrichment_summary.completed} | "
            f"failed="
            f"{enrichment_summary.failed} | "
            f"backlog="
            f"{enrichment_summary.backlog}"
        )


        print(
            "Tokens | "
            f"input="
            f"{enrichment_summary.input_tokens} | "
            f"output="
            f"{enrichment_summary.output_tokens} | "
            f"thought="
            f"{enrichment_summary.thought_tokens} | "
            f"cached="
            f"{enrichment_summary.cached_tokens} | "
            f"total="
            f"{enrichment_summary.total_tokens}"
        )


        print(
            "Snapshots | "
            f"companies="
            f"{snapshot_summary.snapshots_created}"
        )


        print(
            "Hiring stats | "
            f"refreshed="
            f"{hiring_stats_summary.companies_refreshed} | "
            f"publishable="
            f"{hiring_stats_summary.publishable_companies} | "
            f"unpublishable="
            f"{hiring_stats_summary.unpublishable_companies}"
        )


        return pipeline_run_id


    except Exception as exc:

        logger.exception(
            "pipeline_failed "
            "pipeline_run_id=%s",
            pipeline_run_id,
        )


        with get_connection() as conn:

            finish_pipeline_run(
                conn,
                pipeline_run_id,
                "failed",
                metrics,
                str(exc),
            )


        raise


def main() -> None:

    settings = get_settings()


    parser = argparse.ArgumentParser(
        description=(
            "Run the daily Jobly "
            "intelligence pipeline once."
        )
    )


    parser.add_argument(
        "--source-target",
        type=int,
        default=(
            settings.source_target_count
        ),
    )


    parser.add_argument(
        "--source-limit",
        type=int,
        default=(
            settings.crawl_source_limit
        ),
        help=(
            "Optional crawl cap. "
            "Production normally leaves "
            "this unset."
        ),
    )


    parser.add_argument(
        "--enrichment-limit",
        type=int,
        default=(
            settings.ai_enrichment_limit
        ),
        help=(
            "Maximum total queue items "
            "to process with enrichment "
            "during this run."
        ),
    )


    args = parser.parse_args()


    if (
        args.source_target < 1
        or args.enrichment_limit < 1
    ):

        parser.error(
            "source target and enrichment "
            "limit must be at least 1"
        )


    if (
        args.source_limit is not None
        and args.source_limit < 1
    ):

        parser.error(
            "--source-limit must be "
            "at least 1"
        )


    configure_logging()


    run_pipeline(

        source_target=(
            args.source_target
        ),

        source_limit=(
            args.source_limit
        ),

        enrichment_limit=(
            args.enrichment_limit
        ),
    )


if __name__ == "__main__":
    main()