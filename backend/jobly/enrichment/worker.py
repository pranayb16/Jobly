from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobly.config import get_settings
from jobly.db.connection import get_connection
from jobly.enrichment.classifier import classify_job
from jobly.enrichment.deterministic import extract_deterministic_fields
from jobly.enrichment.input_builder import build_classifier_payload
from jobly.enrichment.schemas_v2 import JobEnrichmentV2
from jobly.market.us_scope import classify_us_job


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichmentSummary:
    processed: int
    completed: int
    failed: int
    stale: int
    skipped_non_us: int
    backlog: int


def recover_stale_queue(conn) -> None:
    settings = get_settings()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = CASE WHEN attempts >= %s THEN 'failed' ELSE 'pending' END,
                started_at = NULL,
                last_error = COALESCE(last_error, 'worker_timeout')
            WHERE status = 'processing'
              AND started_at < NOW() - INTERVAL '15 minutes'
            """,
            (settings.ai_max_attempts,),
        )
    conn.commit()


def count_backlog(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM enrichment_queue WHERE status = 'pending'")
        return cur.fetchone()[0]


def claim_next_queue_item(conn) -> dict | None:
    settings = get_settings()
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, job_id, content_hash, priority, reason, attempts
            FROM enrichment_queue
            WHERE status = 'pending' AND attempts < %s
            ORDER BY priority ASC, created_at ASC, id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """,
            (settings.ai_max_attempts,),
        )
        queue_item = cur.fetchone()
        if queue_item is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = 'processing', started_at = NOW(), attempts = attempts + 1,
                last_error = NULL
            WHERE id = %s
            RETURNING attempts
            """,
            (queue_item["id"],),
        )
        queue_item["attempts"] = cur.fetchone()["attempts"]
        cur.execute(
            """
            SELECT id, external_job_id, provider, company, title, location,
                   employment_type, workplace_type, posted_at, posted_at_source,
                   description_text, raw_payload, content_hash
            FROM jobs WHERE id = %s
            """,
            (queue_item["job_id"],),
        )
        job = cur.fetchone()
    conn.commit()
    if job is None:
        return None
    return {**job, "queue_id": queue_item["id"], "queue_hash": queue_item["content_hash"],
            "queue_attempts": queue_item["attempts"], "queue_reason": queue_item["reason"]}


def _complete_queue(conn, queue_id: int, note: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = 'completed', completed_at = NOW(), started_at = NULL, last_error = %s
            WHERE id = %s
            """,
            (note, queue_id),
        )
    conn.commit()


def _mark_non_us(conn, item: dict, reason: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
            SET is_us_job = FALSE, us_location_reason = %s,
                classification_status = 'skipped_non_us',
                classification_started_at = NULL, classification_error = NULL
            WHERE id = %s AND content_hash = %s
            """,
            (reason, item["id"], item["queue_hash"]),
        )
        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = 'completed', completed_at = NOW(), started_at = NULL
            WHERE id = %s
            """,
            (item["queue_id"],),
        )
    conn.commit()


def _legacy_projection(classification) -> dict:
    if isinstance(classification, JobEnrichmentV2):
        skills = list(dict.fromkeys(classification.required_skills + classification.preferred_skills))
        locations = [
            {
                "city": location.city,
                "state": location.region,
                "state_code": None,
                "country": location.country,
                "country_code": location.country_code,
                "remote": classification.workplace_type == "remote",
            }
            for location in classification.locations
        ]
        return {
            "job_family": classification.job_family,
            "job_subfamily": classification.job_subfamily,
            "related_roles": classification.related_roles,
            "skills": skills,
            "seniority": classification.seniority,
            "years_min": classification.years_experience_min,
            "years_max": classification.years_experience_max,
            "locations": locations,
            "confidence": classification.confidence,
        }
    return {
        "job_family": classification.job_family,
        "job_subfamily": classification.job_subfamily,
        "related_roles": classification.related_roles,
        "skills": classification.skills,
        "seniority": classification.seniority,
        "years_min": classification.years_experience_min,
        "years_max": classification.years_experience_max,
        "locations": [location.model_dump() for location in classification.additional_locations],
        "confidence": classification.confidence,
    }


def save_success(conn, item: dict, classification) -> bool:
    settings = get_settings()
    with conn.cursor() as cur:
        cur.execute("SELECT content_hash FROM jobs WHERE id = %s FOR UPDATE", (item["id"],))
        current = cur.fetchone()
        if current is None or current[0] != item["queue_hash"]:
            cur.execute(
                """
                UPDATE enrichment_queue
                SET status = 'completed', completed_at = NOW(), started_at = NULL,
                    last_error = 'stale_content_hash'
                WHERE id = %s
                """,
                (item["queue_id"],),
            )
            conn.commit()
            return False

        data = classification.model_dump(mode="json")
        projection = _legacy_projection(classification)
        cur.execute(
            """
            INSERT INTO job_enrichments (
                job_id, content_hash, schema_version, model, prompt_version, data, confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_id, content_hash, schema_version) DO UPDATE
            SET model = EXCLUDED.model, prompt_version = EXCLUDED.prompt_version,
                data = EXCLUDED.data, confidence = EXCLUDED.confidence, created_at = NOW()
            """,
            (
                item["id"],
                item["queue_hash"],
                settings.ai_classification_version,
                settings.ai_model,
                settings.ai_prompt_version,
                Jsonb(data),
                projection["confidence"],
            ),
        )
        cur.execute(
            """
            UPDATE jobs
            SET job_family = %s, job_subfamily = %s, related_roles = %s, skills = %s,
                seniority = %s, years_experience_min = %s, years_experience_max = %s,
                ai_locations = %s, classification_confidence = %s,
                classification_status = 'ready', classification_version = %s,
                classified_at = NOW(), classified_content_hash = content_hash,
                classification_started_at = NULL, classification_error = NULL, is_us_job = TRUE
            WHERE id = %s AND content_hash = %s
            """,
            (
                projection["job_family"], projection["job_subfamily"],
                Jsonb(projection["related_roles"]), Jsonb(projection["skills"]),
                projection["seniority"], projection["years_min"], projection["years_max"],
                Jsonb(projection["locations"]), projection["confidence"],
                settings.ai_classification_version, item["id"], item["queue_hash"],
            ),
        )
        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = 'completed', completed_at = NOW(), started_at = NULL, last_error = NULL
            WHERE id = %s
            """,
            (item["queue_id"],),
        )
    conn.commit()
    return True


def save_failure(conn, item: dict, error: Exception) -> bool:
    settings = get_settings()
    terminal = item["queue_attempts"] >= settings.ai_max_attempts
    error_message = str(error)[:2000]
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE enrichment_queue
            SET status = %s, started_at = NULL, last_error = %s,
                completed_at = CASE WHEN %s THEN NOW() ELSE NULL END
            WHERE id = %s
            """,
            ("failed" if terminal else "pending", error_message, terminal, item["queue_id"]),
        )
        cur.execute(
            """
            UPDATE jobs
            SET classification_status = %s, classification_started_at = NULL,
                classification_attempts = classification_attempts + 1,
                classification_error = %s
            WHERE id = %s AND content_hash = %s
            """,
            ("failed" if terminal else "pending", error_message, item["id"], item["queue_hash"]),
        )
    conn.commit()
    return terminal


def process_item(conn, item: dict) -> str:
    if item["content_hash"] != item["queue_hash"]:
        _complete_queue(conn, item["queue_id"], "stale_content_hash")
        return "stale"

    decision = classify_us_job(
        provider=item["provider"], location=item["location"], raw=item["raw_payload"]
    )
    if not decision.eligible:
        _mark_non_us(conn, item, decision.reason)
        return "skipped_non_us"

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE jobs SET is_us_job = TRUE, us_location_reason = %s,
                classification_status = 'processing', classification_started_at = NOW()
            WHERE id = %s AND content_hash = %s
            """,
            (decision.reason, item["id"], item["queue_hash"]),
        )
    conn.commit()

    payload = build_classifier_payload(item)
    payload["trusted_structured_context"] = extract_deterministic_fields(item)
    classification = classify_job(
        payload, schema_version=get_settings().ai_classification_version
    )
    return "completed" if save_success(conn, item, classification) else "stale"


def run_enrichment(limit: int | None = None) -> EnrichmentSummary:
    limit = limit or get_settings().ai_enrichment_limit
    if limit < 1:
        raise ValueError("enrichment limit must be at least 1")

    processed = completed = failed = stale = skipped_non_us = 0
    with get_connection() as conn:
        recover_stale_queue(conn)
        while processed < limit:
            item = claim_next_queue_item(conn)
            if item is None:
                break
            processed += 1
            try:
                result = process_item(conn, item)
                completed += int(result in {"completed", "skipped_non_us"})
                stale += int(result == "stale")
                skipped_non_us += int(result == "skipped_non_us")
            except Exception as exc:
                logger.exception("enrichment_failed queue_id=%s job_id=%s", item["queue_id"], item["id"])
                save_failure(conn, item, exc)
                failed += 1
        backlog = count_backlog(conn)

    return EnrichmentSummary(processed, completed, failed, stale, skipped_non_us, backlog)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process the priority enrichment queue.")
    parser.add_argument("--limit", type=int, default=get_settings().ai_enrichment_limit)
    args = parser.parse_args()
    summary = run_enrichment(args.limit)
    print(
        "Enrichment complete | "
        f"processed={summary.processed} | completed={summary.completed} | "
        f"failed={summary.failed} | stale={summary.stale} | backlog={summary.backlog}"
    )


if __name__ == "__main__":
    main()
