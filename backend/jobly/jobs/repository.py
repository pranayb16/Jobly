from __future__ import annotations

from dataclasses import dataclass

from psycopg.types.json import Jsonb

from jobly.companies.repository import ensure_company, link_source_company
from jobly.enrichment.input_builder import build_content_hash


@dataclass(frozen=True)
class DeactivationDecision:
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class JobSaveResult:
    created: bool = False
    changed: bool = False
    reactivated: bool = False


def evaluate_mass_drop(
    previous_job_count: int | None,
    current_job_count: int,
    *,
    minimum_previous_jobs: int = 20,
    minimum_ratio: float = 0.25,
) -> DeactivationDecision:
    if previous_job_count is None or previous_job_count <= 0:
        return DeactivationDecision(allowed=True)
    if current_job_count == 0:
        return DeactivationDecision(
            allowed=False,
            reason=f"zero-job anomaly: previous_job_count={previous_job_count}, current_job_count=0",
        )
    if previous_job_count >= minimum_previous_jobs and current_job_count < (
        previous_job_count * minimum_ratio
    ):
        return DeactivationDecision(
            allowed=False,
            reason=(
                f"mass-drop anomaly: previous_job_count={previous_job_count}, "
                f"current_job_count={current_job_count}, threshold_ratio={minimum_ratio}"
            ),
        )
    return DeactivationDecision(allowed=True)


def trusted_job_count(
    previous_job_count: int | None,
    observed_job_count: int,
    *,
    deactivation_allowed: bool,
) -> int | None:
    """Keep the last trusted baseline when an observed count is anomalous."""
    return observed_job_count if deactivation_allowed else previous_job_count


def enqueue_enrichment(
    cur,
    job_id: int,
    content_hash: str,
    *,
    reason: str,
    priority: int,
) -> None:
    cur.execute(
        """
        INSERT INTO enrichment_queue (job_id, content_hash, priority, reason)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (job_id, content_hash) DO NOTHING
        """,
        (job_id, content_hash, priority, reason),
    )


def _record_event(
    cur,
    job_id: int,
    event_type: str,
    crawl_run_id: int | None,
    pipeline_run_id: int | None,
) -> None:
    cur.execute(
        """
        INSERT INTO job_events (job_id, event_type, crawl_run_id, pipeline_run_id)
        VALUES (%s, %s, %s, %s)
        """,
        (job_id, event_type, crawl_run_id, pipeline_run_id),
    )


def save_job(
    cur,
    source_id: int,
    crawl_run_id: int,
    previous_success_at,
    crawl_started_at,
    job,
    pipeline_run_id: int | None = None,
) -> JobSaveResult:
    content_hash = build_content_hash(job)
    observed_new_after = previous_success_at if job.posted_at is None else None
    observed_new_before = crawl_started_at if observed_new_after is not None else None
    company_id = ensure_company(cur, job.company)
    link_source_company(cur, source_id, company_id)

    cur.execute(
        """
        SELECT id, content_hash, active, title, location, employment_type, workplace_type,
               description_text, description_html, raw_payload, company_id
        FROM jobs
        WHERE source_id = %s AND external_job_id = %s
        FOR UPDATE
        """,
        (source_id, job.external_job_id),
    )
    existing = cur.fetchone()

    if existing is None:
        cur.execute(
            """
            INSERT INTO jobs (
                source_id, company_id, external_job_id, provider, company, title, location,
                employment_type, workplace_type, posted_at, posted_at_source,
                observed_new_after, observed_new_before, description_text,
                description_html, job_url, apply_url, raw_payload, content_hash,
                classification_status, last_seen_crawl_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s
            )
            RETURNING id
            """,
            (
                source_id,
                company_id,
                job.external_job_id,
                job.provider,
                job.company,
                job.title,
                job.location,
                job.employment_type,
                job.workplace_type,
                job.posted_at,
                job.posted_at_source,
                observed_new_after,
                observed_new_before,
                job.description.text,
                job.description.html,
                job.job_url,
                job.apply_url,
                Jsonb(job.raw),
                content_hash,
                crawl_run_id,
            ),
        )
        job_id = cur.fetchone()[0]
        _record_event(cur, job_id, "created", crawl_run_id, pipeline_run_id)
        enqueue_enrichment(cur, job_id, content_hash, reason="new_job", priority=1)
        return JobSaveResult(created=True)

    (
        job_id,
        old_hash,
        was_active,
        old_title,
        old_location,
        old_employment_type,
        old_workplace_type,
        old_description_text,
        old_description_html,
        old_raw_payload,
        old_company_id,
    ) = existing
    changed = old_hash != content_hash

    if changed:
        if old_hash:
            cur.execute(
            """
            INSERT INTO job_versions (
                job_id, content_hash, title, location, employment_type, workplace_type,
                description_text, description_html, raw_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    job_id,
                    old_hash,
                    old_title,
                    old_location,
                    old_employment_type,
                    old_workplace_type,
                    old_description_text,
                    old_description_html,
                    Jsonb(old_raw_payload) if old_raw_payload is not None else None,
                ),
            )
        _record_event(cur, job_id, "changed", crawl_run_id, pipeline_run_id)

    cur.execute(
        """
        UPDATE jobs
        SET company_id = COALESCE(%s, company_id), provider = %s,
            company = COALESCE(%s, company),
            title = %s, location = %s, employment_type = %s, workplace_type = %s,
            posted_at = COALESCE(%s, posted_at),
            posted_at_source = COALESCE(%s, posted_at_source),
            observed_new_after = COALESCE(observed_new_after, %s),
            observed_new_before = COALESCE(observed_new_before, %s),
            description_text = %s, description_html = %s, job_url = %s, apply_url = %s,
            raw_payload = %s, content_hash = %s, last_seen_at = NOW(),
            last_seen_crawl_id = %s, removed_at = NULL, active = TRUE,
            classification_status = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN 'pending' ELSE classification_status END,
            classification_started_at = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN NULL ELSE classification_started_at END,
            classification_attempts = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN 0 ELSE classification_attempts END,
            classification_error = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN NULL ELSE classification_error END,
            classified_at = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN NULL ELSE classified_at END,
            classified_content_hash = CASE WHEN content_hash IS DISTINCT FROM %s
                THEN NULL ELSE classified_content_hash END
        WHERE id = %s
        """,
        (
            company_id or old_company_id,
            job.provider,
            job.company,
            job.title,
            job.location,
            job.employment_type,
            job.workplace_type,
            job.posted_at,
            job.posted_at_source,
            observed_new_after,
            observed_new_before,
            job.description.text,
            job.description.html,
            job.job_url,
            job.apply_url,
            Jsonb(job.raw),
            content_hash,
            crawl_run_id,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            job_id,
        ),
    )

    if changed:
        enqueue_enrichment(cur, job_id, content_hash, reason="changed_job", priority=2)
    if not was_active:
        _record_event(cur, job_id, "reactivated", crawl_run_id, pipeline_run_id)
    return JobSaveResult(changed=changed, reactivated=not was_active)


def mark_missing_jobs_inactive(
    cur,
    source_id: int,
    crawl_run_id: int,
    pipeline_run_id: int | None = None,
) -> int:
    cur.execute(
        """
        WITH removed AS (
            UPDATE jobs
            SET active = FALSE, removed_at = NOW()
            WHERE source_id = %s
              AND active = TRUE
              AND (last_seen_crawl_id IS NULL OR last_seen_crawl_id <> %s)
            RETURNING id
        )
        INSERT INTO job_events (job_id, event_type, crawl_run_id, pipeline_run_id)
        SELECT id, 'removed', %s, %s FROM removed
        """,
        (source_id, crawl_run_id, crawl_run_id, pipeline_run_id),
    )
    return cur.rowcount
