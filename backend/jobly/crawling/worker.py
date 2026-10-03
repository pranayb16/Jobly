from __future__ import annotations

import logging
from dataclasses import dataclass

from jobly.config import get_settings
from jobly.crawling.repository import (
    create_crawl_run,
    mark_crawl_failed,
    mark_crawl_success,
    select_active_sources,
)
from jobly.crawling.runner import crawl_source
from jobly.db.connection import get_connection
from jobly.jobs.repository import (
    evaluate_mass_drop,
    mark_missing_jobs_inactive,
    save_job,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrawlSummary:
    source_count: int
    successful_sources: int
    failed_sources: int
    anomaly_sources: int
    job_count: int
    jobs_new: int = 0
    jobs_changed: int = 0
    jobs_removed: int = 0


def run_crawl(
    source_limit: int | None = None,
    pipeline_run_id: int | None = None,
) -> CrawlSummary:
    settings = get_settings()
    effective_limit = settings.crawl_source_limit if source_limit is None else source_limit
    successful_sources = 0
    failed_sources = 0
    anomaly_sources = 0
    total_jobs = 0
    jobs_new = 0
    jobs_changed = 0
    jobs_removed = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            sources = select_active_sources(cur, effective_limit)

        logger.info("crawl_start source_count=%s source_limit=%s", len(sources), effective_limit)

        for source in sources:
            crawl_run_id = None
            logger.info("source_start source_id=%s provider=%s", source.id, source.provider)
            try:
                crawl_run_id, crawl_started_at = create_crawl_run(
                    conn, source.id, pipeline_run_id
                )
                jobs = crawl_source(source.provider, source.canonical_url)
                decision = evaluate_mass_drop(
                    source.last_job_count,
                    len(jobs),
                    minimum_previous_jobs=settings.mass_drop_min_previous_jobs,
                    minimum_ratio=settings.mass_drop_ratio,
                )

                with conn.cursor() as cur:
                    for job in jobs:
                        result = save_job(
                            cur,
                            source.id,
                            crawl_run_id,
                            source.last_success_at,
                            crawl_started_at,
                            job,
                            pipeline_run_id,
                        )
                        jobs_new += int(result.created)
                        jobs_changed += int(result.changed)

                    if decision.allowed:
                        deactivated = mark_missing_jobs_inactive(
                            cur, source.id, crawl_run_id, pipeline_run_id
                        )
                        jobs_removed += deactivated
                    else:
                        deactivated = 0
                        anomaly_sources += 1
                        logger.warning(
                            "crawl_anomaly source_id=%s provider=%s crawl_run_id=%s status=warning "
                            "job_count=%s reason=%s",
                            source.id,
                            source.provider,
                            crawl_run_id,
                            len(jobs),
                            decision.reason,
                        )

                    mark_crawl_success(
                        cur,
                        source.id,
                        crawl_run_id,
                        len(jobs),
                        warning=decision.reason,
                        update_trusted_count=decision.allowed,
                    )
                conn.commit()

                successful_sources += 1
                total_jobs += len(jobs)
                logger.info(
                    "source_success source_id=%s provider=%s crawl_run_id=%s status=success "
                    "job_count=%s deactivated=%s",
                    source.id,
                    source.provider,
                    crawl_run_id,
                    len(jobs),
                    deactivated,
                )
            except Exception as exc:
                conn.rollback()
                failed_sources += 1
                if crawl_run_id is not None:
                    try:
                        mark_crawl_failed(conn, source.id, crawl_run_id, exc)
                    except Exception:
                        conn.rollback()
                        logger.exception(
                            "crawl_failure_record_failed source_id=%s crawl_run_id=%s",
                            source.id,
                            crawl_run_id,
                        )
                logger.exception(
                    "source_failed source_id=%s provider=%s crawl_run_id=%s status=failed",
                    source.id,
                    source.provider,
                    crawl_run_id,
                )

    summary = CrawlSummary(
        source_count=len(sources),
        successful_sources=successful_sources,
        failed_sources=failed_sources,
        anomaly_sources=anomaly_sources,
        job_count=total_jobs,
        jobs_new=jobs_new,
        jobs_changed=jobs_changed,
        jobs_removed=jobs_removed,
    )
    logger.info(
        "crawl_complete source_count=%s successful=%s failed=%s anomalies=%s job_count=%s",
        summary.source_count,
        summary.successful_sources,
        summary.failed_sources,
        summary.anomaly_sources,
        summary.job_count,
    )
    return summary
