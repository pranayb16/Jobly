from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from jobly.companies.repository import ensure_company
from jobly.crawling.runner import crawl_source
from jobly.db.connection import get_connection


logger = logging.getLogger(__name__)
SUPPORTED_PROVIDERS = {"greenhouse", "ashby", "lever"}
PROVIDER_ALIASES = {
    "ashbyhq": "ashby",
    "breezy hr": "breezy",
    "hrm direct": "hrm_direct",
    "oracle cloud hcm": "oracle_hcm",
    "zoho recruit": "zoho",
}


@dataclass(frozen=True)
class SourceSyncSummary:
    target: int
    active_before: int
    active_after: int
    added: int
    rejected: int
    skipped_existing: int
    candidate_source: str = "database"


def extract_board_id(url: str | None, provider: str | None = None) -> str | None:
    if not url:
        return None

    provider = normalize_provider(provider or "")
    parts = [part for part in urlparse(url).path.split("/") if part]

    # The supported ATS board URLs all identify the board in the first path
    # segment. Keeping these cases explicit avoids accidentally treating a
    # nested job URL as a board URL when another provider is added later.
    if provider in SUPPORTED_PROVIDERS:
        return parts[0] if parts else None

    return parts[0] if parts else None


def normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    return PROVIDER_ALIASES.get(normalized, normalized)


def normalize_url(url: str) -> str:
    return url.strip()


def count_active_sources(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM sources WHERE status = 'active'")
    return cur.fetchone()[0]


def _next_candidate(cur):
    cur.execute(
        """
        UPDATE source_candidates
        SET status = 'pending', updated_at = NOW(),
            validation_error = 'recovered stale validation lease'
        WHERE status = 'validating'
          AND updated_at < NOW() - INTERVAL '30 minutes'
        """
    )
    cur.execute(
        """
        SELECT id, provider, canonical_url, board_id, company_name, status
        FROM source_candidates
        WHERE status IN ('pending', 'valid')
          AND provider = ANY(%s::text[])
          AND canonical_url IS NOT NULL
          AND BTRIM(canonical_url) <> ''
          AND (
              status = 'valid'
              OR last_validated_at IS NULL
              OR last_validated_at < NOW() - INTERVAL '15 minutes'
          )
        ORDER BY CASE status WHEN 'valid' THEN 0 ELSE 1 END, id
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """,
        (sorted(SUPPORTED_PROVIDERS),),
    )
    return cur.fetchone()


def _promote_candidate(conn, candidate, *, validate: bool) -> tuple[bool, bool]:
    candidate_id, provider, url, board_id, company_name, _status = candidate
    if provider not in SUPPORTED_PROVIDERS:
        logger.info(
            "source_candidate_skipped_unsupported_provider id=%s provider=%s",
            candidate_id,
            provider,
        )
        return False, False

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
            transient = isinstance(exc, (requests.RequestException, OSError, TimeoutError))
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE source_candidates
                    SET status = %s, validation_error = %s,
                        last_validated_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    ("pending" if transient else "invalid", str(exc)[:2000], candidate_id),
                )
            conn.commit()
            logger.warning(
                "source_candidate_validation_failed id=%s retryable=%s error=%s",
                candidate_id,
                transient,
                exc,
            )
            return False, not transient
        logger.info("source_candidate_valid id=%s jobs_found=%s", candidate_id, len(jobs))

    with conn.cursor() as cur:
        company_id = ensure_company(cur, company_name)
        source_slug = board_id or extract_board_id(url, provider)
        cur.execute(
            """
            SELECT status
            FROM sources
            WHERE provider = %s AND source_slug = %s
            FOR UPDATE
            """,
            (provider, source_slug),
        )
        existing_source = cur.fetchone()
        was_active = existing_source is not None and existing_source[0] == "active"
        cur.execute(
            """
            INSERT INTO sources (
                provider, source_slug, canonical_url, board_id, company_id, status,
                last_attempt_at, last_error
            ) VALUES (%s, %s, %s, %s, %s, 'active', NOW(), NULL)
            ON CONFLICT (provider, source_slug) WHERE source_slug IS NOT NULL
            DO UPDATE SET
                canonical_url = COALESCE(EXCLUDED.canonical_url, sources.canonical_url),
                board_id = COALESCE(EXCLUDED.board_id, sources.board_id),
                company_id = COALESCE(sources.company_id, EXCLUDED.company_id),
                status = 'active',
                last_attempt_at = NOW(),
                last_error = NULL
            RETURNING id
            """,
            (
                provider,
                source_slug,
                url,
                source_slug,
                company_id,
            ),
        )
        promoted = cur.fetchone() is not None and not was_active
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
    return promoted, False


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
