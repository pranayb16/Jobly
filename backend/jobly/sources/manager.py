from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from jobly.companies.repository import ensure_company
from jobly.crawling.runner import crawl_source
from jobly.db.connection import get_connection


logger = logging.getLogger(__name__)
SUPPORTED_PROVIDERS = {"greenhouse", "ashby", "lever"}


@dataclass(frozen=True)
class SourceSyncSummary:
    target: int
    active_before: int
    active_after: int
    added: int
    rejected: int
    skipped_existing: int
    candidate_source: str = "database"


def extract_board_id(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[0] if parts else None


def normalize_provider(provider: str) -> str:
    return provider.strip().lower()


def normalize_url(url: str) -> str:
    return url.strip()


def count_active_sources(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM sources WHERE status = 'active'")
    return cur.fetchone()[0]


def _next_candidate(cur):
    cur.execute(
        """
        SELECT id, provider, canonical_url, board_id, company_name, status
        FROM source_candidates
        WHERE status IN ('pending', 'valid')
        ORDER BY CASE status WHEN 'valid' THEN 0 ELSE 1 END, id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    )
    return cur.fetchone()


def _promote_candidate(conn, candidate, *, validate: bool) -> tuple[bool, bool]:
    candidate_id, provider, url, board_id, company_name, _status = candidate
    if provider not in SUPPORTED_PROVIDERS:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE source_candidates
                SET status = 'invalid', validation_error = 'unsupported provider',
                    validation_attempts = validation_attempts + 1,
                    last_validated_at = NOW(), updated_at = NOW()
                WHERE id = %s
                """,
                (candidate_id,),
            )
        conn.commit()
        return False, True

    if validate:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE source_candidates
                SET status = 'validating', validation_attempts = validation_attempts + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (candidate_id,),
            )
        conn.commit()
        try:
            jobs = crawl_source(provider, url)
        except Exception as exc:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE source_candidates
                    SET status = 'invalid', validation_error = %s,
                        last_validated_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (str(exc)[:2000], candidate_id),
                )
            conn.commit()
            logger.warning("source_candidate_invalid id=%s error=%s", candidate_id, exc)
            return False, True
        logger.info("source_candidate_valid id=%s jobs_found=%s", candidate_id, len(jobs))

    with conn.cursor() as cur:
        company_id = ensure_company(cur, company_name)
        cur.execute(
            """
            INSERT INTO sources (
                provider, canonical_url, board_id, company_id, status,
                last_attempt_at, last_error
            ) VALUES (%s, %s, %s, %s, 'active', NOW(), NULL)
            ON CONFLICT (provider, canonical_url) DO NOTHING
            RETURNING id
            """,
            (provider, url, board_id or extract_board_id(url), company_id),
        )
        inserted = cur.fetchone() is not None
        if not inserted and company_id is not None:
            cur.execute(
                """
                UPDATE sources
                SET company_id = COALESCE(company_id, %s)
                WHERE provider = %s AND canonical_url = %s
                """,
                (company_id, provider, url),
            )
        cur.execute(
            """
            UPDATE source_candidates
            SET status = 'promoted', validation_error = NULL,
                last_validated_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (candidate_id,),
        )
    conn.commit()
    return inserted, False


def ensure_source_target(target: int) -> SourceSyncSummary:
    if target < 1:
        raise ValueError("Source target must be at least 1")

    with get_connection() as conn:
        with conn.cursor() as cur:
            active_before = count_active_sources(cur)

        if active_before >= target:
            if active_before > target:
                logger.warning(
                    "source_target_below_active_count target=%s active=%s action=none",
                    target,
                    active_before,
                )
            return SourceSyncSummary(target, active_before, active_before, 0, 0, 0)

        active_count = active_before
        added = rejected = skipped = 0
        while active_count < target:
            with conn.cursor() as cur:
                candidate = _next_candidate(cur)
            if candidate is None:
                break
            validate = candidate[5] != "valid"
            inserted, was_rejected = _promote_candidate(conn, candidate, validate=validate)
            rejected += int(was_rejected)
            added += int(inserted)
            skipped += int(not inserted and not was_rejected)
            active_count += int(inserted)

        if active_count < target:
            raise RuntimeError(
                "Unable to reach requested source target from source_candidates. "
                f"target={target}, active={active_count}. Import candidates first."
            )

        summary = SourceSyncSummary(
            target, active_before, active_count, added, rejected, skipped
        )
        logger.info("source_sync_complete summary=%s", summary)
        return summary
