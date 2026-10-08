from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging
from jobly.sources.manager import (
    SUPPORTED_PROVIDERS,
    extract_board_id,
    normalize_provider,
    normalize_url,
)


DEFAULT_INPUT = (
    Path(__file__).resolve().parents[3] / "data" / "raw" / "ats_career_page_urls.csv"
)


@dataclass(frozen=True)
class InventorySource:
    provider: str
    source_slug: str
    canonical_url: str
    board_id: str | None


@dataclass(frozen=True)
class ImportSummary:
    rows_read: int
    unique_sources: int
    inserted: int
    matched_existing: int
    skipped_invalid: int
    provider_counts: dict[str, int]
    dry_run: bool


def _canonical_url(value: object) -> str | None:
    normalized = normalize_url(str(value or ""))
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


def source_slug_for_url(provider: str, canonical_url: str) -> tuple[str, str | None]:
    if provider in SUPPORTED_PROVIDERS:
        board_id = extract_board_id(canonical_url, provider)
        if board_id:
            return board_id, board_id

    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return f"url_{digest}", None


def load_inventory(path: Path) -> tuple[list[InventorySource], int, int]:
    unique: dict[tuple[str, str], InventorySource] = {}
    skipped = 0

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"canonical_url", "ats_platform"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}"
            )

        rows_read = 0
        for row in reader:
            rows_read += 1
            provider = normalize_provider(str(row.get("ats_platform") or ""))
            canonical_url = _canonical_url(row.get("canonical_url"))
            if not provider or canonical_url is None:
                skipped += 1
                continue

            source_slug, board_id = source_slug_for_url(provider, canonical_url)
            source = InventorySource(
                provider=provider,
                source_slug=source_slug,
                canonical_url=canonical_url,
                board_id=board_id,
            )
            unique[(provider, canonical_url)] = source

    return sorted(unique.values(), key=lambda source: (source.provider, source.source_slug)), rows_read, skipped


def upsert_inventory(conn, sources: list[InventorySource]) -> tuple[int, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT provider, source_slug, canonical_url
            FROM sources
            """
        )
        existing_rows = cur.fetchall()
        existing_urls = {(row[0], row[2]) for row in existing_rows}
        existing_slugs = {
            (row[0], row[1]) for row in existing_rows if row[1] is not None
        }

        new_sources = [
            source
            for source in sources
            if (source.provider, source.canonical_url) not in existing_urls
            and (source.provider, source.source_slug) not in existing_slugs
        ]
        cur.executemany(
            """
            INSERT INTO sources (
                provider, source_slug, canonical_url, board_id, status
            ) VALUES (%s, %s, %s, %s, 'not_verified')
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    source.provider,
                    source.source_slug,
                    source.canonical_url,
                    source.board_id,
                )
                for source in new_sources
            ],
        )

    conn.commit()
    return len(new_sources), len(sources) - len(new_sources)


def run_import(path: Path, *, dry_run: bool = False) -> ImportSummary:
    sources, rows_read, skipped = load_inventory(path)
    inserted = matched_existing = 0

    if not dry_run:
        with get_connection() as conn:
            inserted, matched_existing = upsert_inventory(conn, sources)

    return ImportSummary(
        rows_read=rows_read,
        unique_sources=len(sources),
        inserted=inserted,
        matched_existing=matched_existing,
        skipped_invalid=skipped,
        provider_counts=dict(sorted(Counter(source.provider for source in sources).items())),
        dry_run=dry_run,
    )


def print_summary(summary: ImportSummary) -> None:
    suffix = " (dry run)" if summary.dry_run else ""
    print(f"Rows read: {summary.rows_read}")
    print(f"Unique valid sources: {summary.unique_sources}")
    print(f"Inserted as not_verified: {summary.inserted}{suffix}")
    print(f"Matched existing (status preserved): {summary.matched_existing}{suffix}")
    print(f"Skipped invalid: {summary.skipped_invalid}")
    print("By provider:")
    for provider, count in summary.provider_counts.items():
        print(f"  {provider}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import raw ATS career page URLs into the sources inventory."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    configure_logging()
    print_summary(run_import(args.input, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
