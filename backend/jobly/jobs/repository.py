from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from psycopg.types.json import Jsonb

from jobly.companies.repository import ensure_company, link_source_company
from jobly.config import get_settings
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
    baseline: bool = False


ENRICHMENT_WINDOW = timedelta(days=1)


def determine_enrichment_eligibility(
    posted_at: datetime | None,
    *,
    is_us_job: bool | None = None,
    now: datetime | None = None,
) -> tuple[str, str | None]:
    if is_us_job is False:
        return "not_eligible", "non_us"

    if posted_at is None:
        return "not_eligible", "missing_posted_at"

    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    if posted_at < current_time - ENRICHMENT_WINDOW:
        return "not_eligible", "older_than_1_day"

    return "eligible", None


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
    schema_version: str,
) -> None:
    cur.execute(
        """
        INSERT INTO enrichment_queue (
            job_id, content_hash, schema_version, priority, reason
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (job_id, content_hash, schema_version) DO NOTHING
        """,
        (job_id, content_hash, schema_version, priority, reason),
    )


def _record_event(
    cur,
    job_id: int,
    event_type: str,
    crawl_run_id: int | None,
    pipeline_run_id: int | None,
    metadata: dict | None = None,
) -> None:
    cur.execute(
        """
        INSERT INTO job_events (
            job_id,
            event_type,
            crawl_run_id,
            pipeline_run_id,
            metadata
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            job_id,
            event_type,
            crawl_run_id,
            pipeline_run_id,
            Jsonb(metadata or {}),
        ),
    )


def save_job(
    cur,
    source_id: int,
    crawl_run_id: int,
    previous_success_at,
    crawl_started_at,
    job,
    pipeline_run_id: int | None = None,
    *,
    source_company_id: int | None = None,
    source_company_name: str | None = None,
) -> JobSaveResult:
    content_hash = build_content_hash(job)
    schema_version = get_settings().ai_classification_version
    is_baseline = previous_success_at is None
    observed_new_after = previous_success_at if job.posted_at is None else None
    observed_new_before = crawl_started_at if observed_new_after is not None else None
    company_id = source_company_id or ensure_company(cur, job.company)
    company_name = source_company_name or job.company
    if source_company_id is None:
        link_source_company(cur, source_id, company_id)
    eligibility, eligibility_reason = determine_enrichment_eligibility(
        job.posted_at
    )
    classification_status = (
        "pending"
        if eligibility == "eligible"
        else "not_eligible"
    )

    cur.execute(
        """
        SELECT id, content_hash, active, title, location, employment_type, workplace_type,
               description_text, description_html, raw_payload, company_id,
               posted_at, is_us_job
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
                classification_status, enrichment_eligibility,
                enrichment_eligibility_reason, last_seen_crawl_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                source_id,
                company_id,
                job.external_job_id,
                job.provider,
                company_name,
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
                classification_status,
                eligibility,
                eligibility_reason,
                crawl_run_id,
            ),
        )
        job_id = cur.fetchone()[0]
        _record_event(
            cur,
            job_id,
            "created",
            crawl_run_id,
            pipeline_run_id,
            metadata={"baseline": is_baseline},
        )

        if eligibility == "eligible":
            if is_baseline:
                enqueue_enrichment(
                    cur,
                    job_id,
                    content_hash,
                    reason="bootstrap",
                    priority=3,
                    schema_version=schema_version,
                )
            else:
                enqueue_enrichment(
                    cur,
                    job_id,
                    content_hash,
                    reason="new_job",
                    priority=1,
                    schema_version=schema_version,
                )

        return JobSaveResult(
            created=True,
            baseline=is_baseline,
        )

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
        old_posted_at,
        is_us_job,
    ) = existing
    changed = old_hash != content_hash
    eligibility, eligibility_reason = determine_enrichment_eligibility(
        job.posted_at or old_posted_at,
        is_us_job=is_us_job,
    )

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
            enrichment_eligibility = %s,
            enrichment_eligibility_reason = %s,
            classification_status = CASE
                WHEN %s = 'not_eligible' THEN 'not_eligible'
                WHEN content_hash IS DISTINCT FROM %s THEN 'pending'
                ELSE classification_status END,
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
            company_name,
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
            eligibility,
            eligibility_reason,
            eligibility,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            content_hash,
            job_id,
        ),
    )

    if changed and eligibility == "eligible":
        enqueue_enrichment(
            cur,
            job_id,
            content_hash,
            reason="changed_job",
            priority=2,
            schema_version=schema_version,
        )
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
