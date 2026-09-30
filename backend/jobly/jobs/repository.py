from __future__ import annotations

from dataclasses import dataclass

from psycopg.types.json import Jsonb

from jobly.enrichment.input_builder import build_content_hash


@dataclass(frozen=True)
class DeactivationDecision:
    allowed: bool
    reason: str | None = None


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
    if (
        previous_job_count >= minimum_previous_jobs
        and current_job_count < previous_job_count * minimum_ratio
    ):
        return DeactivationDecision(
            allowed=False,
            reason=(
                f"mass-drop anomaly: previous_job_count={previous_job_count}, "
                f"current_job_count={current_job_count}, threshold_ratio={minimum_ratio}"
            ),
        )
    return DeactivationDecision(allowed=True)


def save_job(
    cur,
    source_id: int,
    crawl_run_id: int,
    previous_success_at,
    crawl_started_at,
    job,
) -> None:
    content_hash = build_content_hash(job)
    observed_new_after = None
    observed_new_before = None

    if job.posted_at is None and previous_success_at is not None:
        observed_new_after = previous_success_at
        observed_new_before = crawl_started_at

    cur.execute(
        """
        INSERT INTO jobs (
            source_id, external_job_id, provider, company, title, location,
            employment_type, workplace_type, posted_at, posted_at_source,
            observed_new_after, observed_new_before, description_text,
            description_html, job_url, apply_url, raw_payload, content_hash,
            classification_status, last_seen_crawl_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s
        )
        ON CONFLICT (source_id, external_job_id)
        DO UPDATE SET
            provider = EXCLUDED.provider,
            company = EXCLUDED.company,
            title = EXCLUDED.title,
            location = EXCLUDED.location,
            employment_type = EXCLUDED.employment_type,
            workplace_type = EXCLUDED.workplace_type,
            posted_at = COALESCE(EXCLUDED.posted_at, jobs.posted_at),
            posted_at_source = COALESCE(EXCLUDED.posted_at_source, jobs.posted_at_source),
            observed_new_after = COALESCE(jobs.observed_new_after, EXCLUDED.observed_new_after),
            observed_new_before = COALESCE(jobs.observed_new_before, EXCLUDED.observed_new_before),
            description_text = EXCLUDED.description_text,
            description_html = EXCLUDED.description_html,
            job_url = EXCLUDED.job_url,
            apply_url = EXCLUDED.apply_url,
            raw_payload = EXCLUDED.raw_payload,
            classification_status = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN 'pending'
                ELSE jobs.classification_status
            END,
            classification_started_at = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN NULL
                ELSE jobs.classification_started_at
            END,
            classification_attempts = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN 0
                ELSE jobs.classification_attempts
            END,
            classification_error = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN NULL
                ELSE jobs.classification_error
            END,
            classified_at = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN NULL
                ELSE jobs.classified_at
            END,
            classified_content_hash = CASE
                WHEN jobs.content_hash IS DISTINCT FROM EXCLUDED.content_hash THEN NULL
                ELSE jobs.classified_content_hash
            END,
            content_hash = EXCLUDED.content_hash,
            last_seen_at = NOW(),
            last_seen_crawl_id = EXCLUDED.last_seen_crawl_id,
            removed_at = NULL,
            active = TRUE
        """,
        (
            source_id,
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


def mark_missing_jobs_inactive(cur, source_id: int, crawl_run_id: int) -> int:
    cur.execute(
        """
        UPDATE jobs
        SET active = FALSE, removed_at = NOW()
        WHERE source_id = %s
          AND active = TRUE
          AND (last_seen_crawl_id IS NULL OR last_seen_crawl_id <> %s)
        """,
        (source_id, crawl_run_id),
    )
    return cur.rowcount
