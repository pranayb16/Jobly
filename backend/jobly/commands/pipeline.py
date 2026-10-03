from __future__ import annotations

import argparse
import logging
from pathlib import Path

from jobly.commands.migrate import DEFAULT_MIGRATIONS_DIR, run_migrations
from jobly.config import get_settings
from jobly.crawling.worker import run_crawl
from jobly.db.connection import get_connection
from jobly.enrichment.worker import run_enrichment
from jobly.intelligence.snapshots import build_snapshots
from jobly.logging_config import configure_logging
from jobly.pipeline.repository import (
    create_pipeline_run,
    ensure_pipeline_run_table,
    finish_pipeline_run,
)
from jobly.sources.manager import ensure_source_target


logger = logging.getLogger(__name__)


def determine_pipeline_status(
    *, crawl_failures: int, enrichment_failures: int, enrichment_backlog: int
) -> str:
    del enrichment_backlog  # Backlog is an expected bounded-work condition, not a failure.
    return "partial_success" if crawl_failures or enrichment_failures else "success"


def run_pipeline(
    *,
    source_target: int,
    source_limit: int | None,
    enrichment_limit: int,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> int:
    with get_connection() as conn:
        ensure_pipeline_run_table(conn)
        pipeline_run_id = create_pipeline_run(conn, source_target)

    metrics: dict[str, int] = {}
    try:
        run_migrations(migrations_dir)
        source_summary = ensure_source_target(source_target)
        crawl_summary = run_crawl(source_limit, pipeline_run_id)
        enrichment_summary = run_enrichment(enrichment_limit)
        snapshot_summary = build_snapshots()
        metrics = {
            "sources_attempted": crawl_summary.source_count,
            "sources_successful": crawl_summary.successful_sources,
            "sources_failed": crawl_summary.failed_sources,
            "jobs_seen": crawl_summary.job_count,
            "jobs_new": crawl_summary.jobs_new,
            "jobs_changed": crawl_summary.jobs_changed,
            "jobs_removed": crawl_summary.jobs_removed,
            "enrichments_processed": enrichment_summary.processed,
            "enrichments_completed": enrichment_summary.completed,
            "enrichments_failed": enrichment_summary.failed,
            "enrichment_backlog": enrichment_summary.backlog,
            "snapshots_created": snapshot_summary.snapshots_created,
        }
        status = determine_pipeline_status(
            crawl_failures=crawl_summary.failed_sources,
            enrichment_failures=enrichment_summary.failed,
            enrichment_backlog=enrichment_summary.backlog,
        )
        with get_connection() as conn:
            finish_pipeline_run(conn, pipeline_run_id, status, metrics)
        logger.info(
            "pipeline_complete pipeline_run_id=%s status=%s source_sync=%s metrics=%s",
            pipeline_run_id,
            status,
            source_summary,
            metrics,
        )
        return pipeline_run_id
    except Exception as exc:
        logger.exception("pipeline_failed pipeline_run_id=%s", pipeline_run_id)
        with get_connection() as conn:
            finish_pipeline_run(conn, pipeline_run_id, "failed", metrics, str(exc))
        raise


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the daily Jobly intelligence pipeline once.")
    parser.add_argument("--source-target", type=int, default=settings.source_target_count)
    parser.add_argument(
        "--source-limit",
        type=int,
        default=settings.crawl_source_limit,
        help="Optional development-only crawl cap; production should leave this unset.",
    )
    parser.add_argument("--enrichment-limit", type=int, default=settings.ai_enrichment_limit)
    args = parser.parse_args()
    if args.source_target < 1 or args.enrichment_limit < 1:
        parser.error("source target and enrichment limit must be at least 1")
    if args.source_limit is not None and args.source_limit < 1:
        parser.error("source limit must be at least 1")
    configure_logging()
    run_pipeline(
        source_target=args.source_target,
        source_limit=args.source_limit,
        enrichment_limit=args.enrichment_limit,
    )


if __name__ == "__main__":
    main()
