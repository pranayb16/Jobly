from __future__ import annotations

import csv
import logging

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from jobly.crawling.runner import (
    crawl_source,
)
from jobly.db.connection import (
    get_connection,
)


logger = logging.getLogger(
    __name__
)


REPO_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)


# Prefer your already-verified source set.
# If that isn't present, fall back progressively.
CANDIDATE_FILES = [
    REPO_ROOT
    / "data"
    / "cleaned"
    / "valid_sources.csv",

    REPO_ROOT
    / "data"
    / "cleaned"
    / "supported_sources.csv",

    REPO_ROOT
    / "data"
    / "raw"
    / "ats_career_page_urls.csv",
]


SUPPORTED_PROVIDERS = {
    "greenhouse",
    "ashby",
    "lever",
}


@dataclass(frozen=True)
class SourceSyncSummary:
    target: int
    active_before: int
    active_after: int
    added: int
    rejected: int
    skipped_existing: int
    candidate_file: str


def extract_board_id(
    url: str,
) -> str | None:

    parts = [
        part
        for part
        in urlparse(url).path.split("/")
        if part
    ]

    return (
        parts[0]
        if parts
        else None
    )


def resolve_candidate_file() -> Path:

    for path in CANDIDATE_FILES:

        if path.exists():

            logger.info(
                "source_registry_selected path=%s",
                path,
            )

            return path

    raise FileNotFoundError(
        (
            "No source CSV found. Expected one of: "
            + ", ".join(
                str(path)
                for path in CANDIDATE_FILES
            )
        )
    )


def normalize_provider(
    provider: str,
) -> str:

    return (
        provider
        .strip()
        .lower()
    )


def normalize_url(
    url: str,
) -> str:

    return url.strip()


def count_active_sources(
    cur,
) -> int:

    cur.execute(
        """
        SELECT COUNT(*)

        FROM sources

        WHERE status = 'active'
        """
    )

    return cur.fetchone()[0]


def load_existing_sources(
    cur,
) -> set[tuple[str, str]]:

    cur.execute(
        """
        SELECT
            provider,
            canonical_url

        FROM sources
        """
    )

    return {
        (
            provider.strip().lower(),
            canonical_url.strip(),
        )

        for provider, canonical_url
        in cur.fetchall()
    }


def load_candidates(
    path: Path,
):

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        for row in reader:

            provider = normalize_provider(
                row.get(
                    "ats_platform",
                    "",
                )
            )

            url = normalize_url(
                row.get(
                    "canonical_url",
                    "",
                )
            )

            if (
                provider
                not in SUPPORTED_PROVIDERS
            ):
                continue

            if not url:
                continue

            yield (
                provider,
                url,
            )


def record_valid_source(
    conn,
    provider: str,
    url: str,
) -> bool:

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO sources (
                provider,
                canonical_url,
                board_id,
                status,
                last_attempt_at,
                last_error
            )

            VALUES (
                %s,
                %s,
                %s,
                'active',
                NOW(),
                NULL
            )

            ON CONFLICT (
                provider,
                canonical_url
            )

            DO NOTHING

            RETURNING id
            """,
            (
                provider,
                url,
                extract_board_id(
                    url
                ),
            ),
        )

        inserted = (
            cur.fetchone()
            is not None
        )

    conn.commit()

    return inserted


def record_invalid_source(
    conn,
    provider: str,
    url: str,
    error: Exception,
) -> None:

    error_message = (
        str(error)[:2000]
    )

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO sources (
                provider,
                canonical_url,
                board_id,
                status,
                last_attempt_at,
                last_failure_at,
                last_error
            )

            VALUES (
                %s,
                %s,
                %s,
                'invalid',
                NOW(),
                NOW(),
                %s
            )

            ON CONFLICT (
                provider,
                canonical_url
            )

            DO NOTHING
            """,
            (
                provider,
                url,
                extract_board_id(
                    url
                ),
                error_message,
            ),
        )

    conn.commit()


def ensure_source_target(
    target: int,
) -> SourceSyncSummary:

    if target < 1:

        raise ValueError(
            "Source target must be at least 1"
        )


    candidate_file = (
        resolve_candidate_file()
    )


    with get_connection() as conn:

        with conn.cursor() as cur:

            active_before = (
                count_active_sources(
                    cur
                )
            )

            existing = (
                load_existing_sources(
                    cur
                )
            )


        logger.info(
            (
                "source_sync_start "
                "target=%s "
                "active=%s "
                "missing=%s "
                "candidate_file=%s"
            ),
            target,
            active_before,
            max(
                0,
                target - active_before,
            ),
            candidate_file,
        )


        # Already enough sources.
        if (
            active_before
            >= target
        ):

            return SourceSyncSummary(
                target=target,
                active_before=active_before,
                active_after=active_before,
                added=0,
                rejected=0,
                skipped_existing=0,
                candidate_file=str(
                    candidate_file
                ),
            )


        active_count = (
            active_before
        )

        added = 0
        rejected = 0
        skipped_existing = 0


        for provider, url in load_candidates(
            candidate_file
        ):

            if (
                active_count
                >= target
            ):
                break


            key = (
                provider,
                url,
            )


            # Includes active, invalid, disabled,
            # etc. We don't repeatedly retry known
            # failed sources every pipeline run.
            if key in existing:

                skipped_existing += 1

                continue


            logger.info(
                (
                    "source_validation_start "
                    "provider=%s "
                    "url=%s "
                    "active=%s "
                    "target=%s"
                ),
                provider,
                url,
                active_count,
                target,
            )


            try:

                # This is a real ATS API call.
                #
                # Success with zero jobs is still
                # considered a valid career board.
                jobs = crawl_source(
                    provider,
                    url,
                )


            except Exception as exc:

                rejected += 1

                record_invalid_source(
                    conn,
                    provider,
                    url,
                    exc,
                )

                existing.add(
                    key
                )

                logger.warning(
                    (
                        "source_validation_failed "
                        "provider=%s "
                        "url=%s "
                        "error=%s"
                    ),
                    provider,
                    url,
                    str(exc)[:500],
                )

                continue


            inserted = (
                record_valid_source(
                    conn,
                    provider,
                    url,
                )
            )


            existing.add(
                key
            )


            if inserted:

                added += 1

                active_count += 1


            logger.info(
                (
                    "source_validation_success "
                    "provider=%s "
                    "url=%s "
                    "jobs_found=%s "
                    "active=%s "
                    "target=%s"
                ),
                provider,
                url,
                len(jobs),
                active_count,
                target,
            )


        if (
            active_count
            < target
        ):

            raise RuntimeError(
                (
                    "Unable to reach requested "
                    "source target. "
                    f"target={target}, "
                    f"active={active_count}, "
                    f"candidate_file={candidate_file}"
                )
            )


        summary = SourceSyncSummary(
            target=target,
            active_before=active_before,
            active_after=active_count,
            added=added,
            rejected=rejected,
            skipped_existing=skipped_existing,
            candidate_file=str(
                candidate_file
            ),
        )


        logger.info(
            (
                "source_sync_complete "
                "target=%s "
                "active_before=%s "
                "active_after=%s "
                "added=%s "
                "rejected=%s "
                "skipped_existing=%s"
            ),
            summary.target,
            summary.active_before,
            summary.active_after,
            summary.added,
            summary.rejected,
            summary.skipped_existing,
        )


        return summary