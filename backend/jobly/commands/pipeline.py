from __future__ import annotations

import argparse
import logging
from pathlib import Path

from jobly.commands.migrate import (
    DEFAULT_MIGRATIONS_DIR,
    run_migrations,
)
from jobly.config import get_settings
from jobly.crawling.worker import run_crawl
from jobly.db.connection import get_connection
from jobly.enrichment.worker import run_enrichment
from jobly.intelligence.hiring_stats import (
    refresh_hiring_stats,
)
from jobly.intelligence.snapshots import (
    build_snapshots,
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
    record_event,
    start_stage,
)
from jobly.pipeline.repository import (
    create_pipeline_run,
    ensure_pipeline_run_table,
    finish_pipeline_run,
)
from jobly.sources.manager import (
    ensure_source_target,
)


logger = logging.getLogger(__name__)


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
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> int:

    # ---------------------------------------------------------
    # Create parent pipeline run.
    #
    # pipeline_runs must exist before migrations because
    # migrations themselves are part of the pipeline.
    # ---------------------------------------------------------

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

        # =====================================================
        # 1. MIGRATIONS
        #
        # Observability tables may not exist until migration
        # 019 is applied, so database logging is enabled only
        # after migrations finish.
        # =====================================================

        run_migrations(
            migrations_dir
        )

        enable_pipeline_database_logging()


        # =====================================================
        # 2. SOURCE SYNC
        # =====================================================

        set_pipeline_stage(
            "source_sync"
        )

        start_stage(
            pipeline_run_id,
            "source_sync",
        )

        try:

            source_summary = (
                ensure_source_target(
                    source_target
                )
            )

            finish_stage(
                pipeline_run_id,
                "source_sync",
                status="success",
                metrics={
                    "target":
                        source_summary.target,

                    "active_before":
                        source_summary.active_before,

                    "active_after":
                        source_summary.active_after,

                    "added":
                        source_summary.added,

                    "rejected":
                        source_summary.rejected,

                    "skipped_existing":
                        source_summary.skipped_existing,

                    "candidate_source":
                        source_summary.candidate_source,
                },
            )

        except Exception as exc:

            finish_stage(
                pipeline_run_id,
                "source_sync",
                status="failed",
                error=str(exc),
            )

            raise


        # =====================================================
        # 3. CRAWL
        # =====================================================

        set_pipeline_stage(
            "crawl"
        )

        start_stage(
            pipeline_run_id,
            "crawl",
        )

        try:

            crawl_summary = run_crawl(
                source_limit,
                pipeline_run_id,
            )

            crawl_stage_status = (
                "partial_success"
                if crawl_summary.failed_sources
                else "success"
            )

            finish_stage(
                pipeline_run_id,
                "crawl",
                status=crawl_stage_status,
                metrics={
                    "sources_attempted":
                        crawl_summary.source_count,

                    "sources_successful":
                        crawl_summary.successful_sources,

                    "sources_failed":
                        crawl_summary.failed_sources,

                    "anomaly_sources":
                        crawl_summary.anomaly_sources,

                    "jobs_seen":
                        crawl_summary.job_count,

                    "jobs_new":
                        crawl_summary.jobs_new,

                    "jobs_changed":
                        crawl_summary.jobs_changed,

                    "jobs_removed":
                        crawl_summary.jobs_removed,
                },
            )

        except Exception as exc:

            finish_stage(
                pipeline_run_id,
                "crawl",
                status="failed",
                error=str(exc),
            )

            raise


        # =====================================================
        # 4. ENRICHMENT
        # =====================================================

        set_pipeline_stage(
            "enrichment"
        )

        start_stage(
            pipeline_run_id,
            "enrichment",
        )

        try:

            enrichment_summary = (
                run_enrichment(
                    enrichment_limit,
                    pipeline_run_id,
                )
            )

            enrichment_stage_status = (
                "partial_success"
                if enrichment_summary.failed
                else "success"
            )

            finish_stage(
                pipeline_run_id,
                "enrichment",
                status=enrichment_stage_status,
                metrics={
                    "processed":
                        enrichment_summary.processed,

                    "ai_calls":
                        enrichment_summary.ai_calls,

                    "completed":
                        enrichment_summary.completed,

                    "failed":
                        enrichment_summary.failed,

                    "stale":
                        enrichment_summary.stale,

                    "skipped_non_us":
                        enrichment_summary.skipped_non_us,

                    "backlog":
                        enrichment_summary.backlog,

                    "models":
                        enrichment_summary.model_counts,

                    "input_tokens":
                        enrichment_summary.input_tokens,

                    "output_tokens":
                        enrichment_summary.output_tokens,

                    "thought_tokens":
                        enrichment_summary.thought_tokens,

                    "cached_tokens":
                        enrichment_summary.cached_tokens,

                    "total_tokens":
                        enrichment_summary.total_tokens,
                },
            )

        except Exception as exc:

            finish_stage(
                pipeline_run_id,
                "enrichment",
                status="failed",
                error=str(exc),
            )

            raise


        # =====================================================
        # 5. SNAPSHOTS
        #
        # Retained for internal compatibility/history.
        #
        # company_hiring_stats does NOT depend on snapshots.
        # =====================================================

        set_pipeline_stage(
            "snapshots"
        )

        start_stage(
            pipeline_run_id,
            "snapshots",
        )

        try:

            snapshot_summary = (
                build_snapshots()
            )

            finish_stage(
                pipeline_run_id,
                "snapshots",
                status="success",
                metrics={
                    "companies":
                        snapshot_summary
                        .snapshots_created,
                },
            )

        except Exception as exc:

            finish_stage(
                pipeline_run_id,
                "snapshots",
                status="failed",
                error=str(exc),
            )

            raise


        # =====================================================
        # 6. HIRING STATISTICS
        #
        # Deterministic product statistics calculated from:
        #
        # jobs.posted_at
        # jobs.active
        #
        # This does not depend on AI or snapshots.
        # =====================================================

        set_pipeline_stage(
            "hiring_stats"
        )

        start_stage(
            pipeline_run_id,
            "hiring_stats",
        )

        try:

            hiring_stats_summary = (
                refresh_hiring_stats()
            )

            finish_stage(
                pipeline_run_id,
                "hiring_stats",
                status="success",
                metrics={
                    "companies_refreshed":
                        hiring_stats_summary
                        .companies_refreshed,

                    "publishable":
                        hiring_stats_summary
                        .publishable_companies,

                    "unpublishable":
                        hiring_stats_summary
                        .unpublishable_companies,
                },
            )

        except Exception as exc:

            finish_stage(
                pipeline_run_id,
                "hiring_stats",
                status="failed",
                error=str(exc),
            )

            raise


        # =====================================================
        # 7. FINAL PIPELINE METRICS
        # =====================================================

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

            "enrichment_backlog":
                enrichment_summary.backlog,

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


        # -----------------------------------------------------
        # Pipeline-level log
        # -----------------------------------------------------

        set_pipeline_stage(
            "pipeline"
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


        # -----------------------------------------------------
        # Human-readable terminal output
        # -----------------------------------------------------

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
            f"successful="
            f"{crawl_summary.successful_sources} | "
            f"failed="
            f"{crawl_summary.failed_sources} | "
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
            f"skipped_non_us="
            f"{enrichment_summary.skipped_non_us} | "
            f"backlog="
            f"{enrichment_summary.backlog}"
        )


        print(
            "Models | "
            f"{enrichment_summary.model_counts}"
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


        set_pipeline_stage(
            None
        )

        return pipeline_run_id


    except Exception as exc:

        # -----------------------------------------------------
        # Pipeline-level failure
        # -----------------------------------------------------

        set_pipeline_stage(
            "pipeline"
        )

        logger.exception(
            "pipeline_failed "
            "pipeline_run_id=%s",
            pipeline_run_id,
        )


        # Structured high-level error.
        #
        # record_event() is deliberately failure-safe and will
        # not take down the pipeline if observability storage
        # itself has a problem.
        record_event(
            pipeline_run_id=(
                pipeline_run_id
            ),
            stage="pipeline",
            severity="critical",
            event_type="pipeline_failed",
            message=str(exc),
        )


        with get_connection() as conn:

            finish_pipeline_run(
                conn,
                pipeline_run_id,
                "failed",
                metrics,
                str(exc),
            )


        set_pipeline_stage(
            None
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
            "Maximum number of actual AI "
            "classifications during this run."
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