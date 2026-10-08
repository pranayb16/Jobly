from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging
from jobly.sources.manager import (
    SUPPORTED_PROVIDERS,
    extract_board_id,
    normalize_provider,
    normalize_url,
)


DEFAULT_INPUT = Path(__file__).resolve().parents[3] / "data" / "cleaned" / "valid_sources.csv"
REPORT_PROVIDERS = (
    "greenhouse",
    "ashby",
    "lever",
    "workday",
    "rippling",
    "smartrecruiters",
    "gem",
)


@dataclass(frozen=True)
class SourceCandidate:
    provider: str
    source_slug: str
    canonical_url: str | None
    company_name: str | None
    board_id: str
    origins: frozenset[str] = field(default_factory=frozenset)
    status: str = "pending"


@dataclass(frozen=True)
class ImportReport:
    csv_rows_read: int
    parquet_rows_read: int
    normalized_candidates: int
    duplicates_merged: int
    inserted: int
    updated: int
    sources_inserted: int
    sources_updated: int
    skipped_invalid_missing_keys: int
    provider_counts: dict[str, int]
    csv_only: int
    parquet_only: int
    overlapping: int
    supported_pending: int
    unsupported_pending: int
    with_canonical_url: int
    without_canonical_url: int
    dry_run: bool


@dataclass
class _CandidateParts:
    provider: str
    source_slug: str
    csv_url: str | None = None
    parquet_url: str | None = None
    csv_company_name: str | None = None
    parquet_company_name: str | None = None
    origins: set[str] = field(default_factory=set)


UPSERT_SQL = """
    INSERT INTO source_candidates (
        provider,
        source_slug,
        canonical_url,
        board_id,
        company_name,
        status
    ) VALUES (%s, %s, %s, %s, %s, 'pending')
    ON CONFLICT (provider, source_slug) WHERE source_slug IS NOT NULL
    DO UPDATE SET
        canonical_url = COALESCE(
            EXCLUDED.canonical_url,
            source_candidates.canonical_url
        ),
        board_id = COALESCE(
            EXCLUDED.board_id,
            source_candidates.board_id
        ),
        company_name = COALESCE(
            EXCLUDED.company_name,
            source_candidates.company_name
        ),
        status = CASE
            WHEN %s THEN source_candidates.status
            ELSE 'pending'
        END,
        validation_error = CASE
            WHEN %s THEN source_candidates.validation_error
            ELSE NULL
        END,
        validation_attempts = CASE
            WHEN %s THEN source_candidates.validation_attempts
            ELSE 0
        END,
        last_validated_at = CASE
            WHEN %s THEN source_candidates.last_validated_at
            ELSE NULL
        END,
        updated_at = NOW()
"""


UPSERT_SOURCES_SQL = """
    INSERT INTO sources (
        provider,
        source_slug,
        canonical_url,
        board_id,
        status
    ) VALUES (%s, %s, %s, %s, 'not_verified')
    ON CONFLICT (provider, source_slug) WHERE source_slug IS NOT NULL
    DO UPDATE SET
        canonical_url = COALESCE(
            EXCLUDED.canonical_url,
            sources.canonical_url
        ),
        board_id = COALESCE(
            EXCLUDED.board_id,
            sources.board_id
        )
"""


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def normalize_source_slug(value: object) -> str:
    return _optional_text(value) or ""


def normalize_candidate_url(value: object) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    normalized = normalize_url(normalized)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return normalized


def source_slug_from_url(provider: str, canonical_url: str | None) -> str:
    return normalize_source_slug(extract_board_id(canonical_url, provider))


def load_csv_candidates(path: Path) -> tuple[list[SourceCandidate], int, int]:
    candidates: list[SourceCandidate] = []
    skipped = 0

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"ats_platform", "canonical_url", "company_name"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}"
            )

        rows_read = 0
        for row in reader:
            rows_read += 1
            provider = normalize_provider(_optional_text(row.get("ats_platform")) or "")
            canonical_url = normalize_candidate_url(row.get("canonical_url"))
            source_slug = source_slug_from_url(provider, canonical_url)

            if not provider or not source_slug:
                skipped += 1
                continue

            candidates.append(
                SourceCandidate(
                    provider=provider,
                    source_slug=source_slug,
                    canonical_url=canonical_url,
                    company_name=_optional_text(row.get("company_name")),
                    board_id=source_slug,
                    origins=frozenset({"csv"}),
                )
            )

    return candidates, rows_read, skipped


def load_parquet_candidates(path: Path) -> tuple[list[SourceCandidate], int, int]:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - dependency failure path
        raise RuntimeError(
            "Reading companies.parquet requires the duckdb package. "
            "Install the project dependencies before running this importer."
        ) from exc

    connection = duckdb.connect()
    try:
        columns = {
            row[0]
            for row in connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(path)],
            ).fetchall()
        }
        required = {"ats", "slug", "name", "career_url"}
        missing = required.difference(columns)
        if missing:
            raise ValueError(
                f"Parquet file is missing required columns: {', '.join(sorted(missing))}"
            )

        rows = connection.execute(
            """
            SELECT ats, slug, name, career_url
            FROM read_parquet(?)
            """,
            [str(path)],
        ).fetchall()
    finally:
        connection.close()

    candidates: list[SourceCandidate] = []
    skipped = 0
    for ats, slug, name, career_url in rows:
        provider = normalize_provider(_optional_text(ats) or "")
        source_slug = normalize_source_slug(slug)
        canonical_url = normalize_candidate_url(career_url)

        if not provider or not source_slug:
            skipped += 1
            continue

        candidates.append(
            SourceCandidate(
                provider=provider,
                source_slug=source_slug,
                canonical_url=canonical_url,
                company_name=_optional_text(name),
                board_id=(
                    extract_board_id(canonical_url, provider)
                    if provider in SUPPORTED_PROVIDERS and canonical_url
                    else source_slug
                )
                or source_slug,
                origins=frozenset({"parquet"}),
            )
        )

    return candidates, len(rows), skipped


def merge_candidates(
    csv_candidates: Iterable[SourceCandidate],
    parquet_candidates: Iterable[SourceCandidate],
) -> tuple[list[SourceCandidate], int]:
    csv_candidates = list(csv_candidates)
    parquet_candidates = list(parquet_candidates)
    merged: dict[tuple[str, str], _CandidateParts] = {}

    for origin, candidates in (
        ("csv", csv_candidates),
        ("parquet", parquet_candidates),
    ):
        for candidate in candidates:
            key = (candidate.provider, candidate.source_slug)
            parts = merged.setdefault(
                key,
                _CandidateParts(
                    provider=candidate.provider,
                    source_slug=candidate.source_slug,
                ),
            )
            parts.origins.add(origin)

            if origin == "csv":
                parts.csv_url = parts.csv_url or candidate.canonical_url
                parts.csv_company_name = (
                    parts.csv_company_name or candidate.company_name
                )
            else:
                parts.parquet_url = parts.parquet_url or candidate.canonical_url
                parts.parquet_company_name = (
                    parts.parquet_company_name or candidate.company_name
                )

    normalized = []
    for parts in merged.values():
        canonical_url = parts.csv_url or parts.parquet_url
        company_name = parts.parquet_company_name or parts.csv_company_name
        board_id = (
            extract_board_id(canonical_url, parts.provider)
            if parts.provider in SUPPORTED_PROVIDERS and canonical_url
            else parts.source_slug
        ) or parts.source_slug
        normalized.append(
            SourceCandidate(
                provider=parts.provider,
                source_slug=parts.source_slug,
                canonical_url=canonical_url,
                company_name=company_name,
                board_id=board_id,
                origins=frozenset(parts.origins),
            )
        )

    normalized.sort(key=lambda candidate: (candidate.provider, candidate.source_slug))
    duplicates_merged = len(csv_candidates) + len(parquet_candidates) - len(normalized)
    return normalized, duplicates_merged


def upsert_candidates(conn, candidates: list[SourceCandidate]) -> tuple[int, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT provider, source_slug
            FROM source_candidates
            WHERE source_slug IS NOT NULL
            """
        )
        existing_keys = {(row[0], row[1]) for row in cur.fetchall()}
        params = [
            (
                candidate.provider,
                candidate.source_slug,
                candidate.canonical_url,
                candidate.board_id,
                candidate.company_name,
                candidate.provider in SUPPORTED_PROVIDERS,
                candidate.provider in SUPPORTED_PROVIDERS,
                candidate.provider in SUPPORTED_PROVIDERS,
                candidate.provider in SUPPORTED_PROVIDERS,
            )
            for candidate in candidates
        ]
        cur.executemany(UPSERT_SQL, params)

    conn.commit()
    inserted = sum(
        (candidate.provider, candidate.source_slug) not in existing_keys
        for candidate in candidates
    )
    return inserted, len(candidates) - inserted


def upsert_sources(conn, candidates: list[SourceCandidate]) -> tuple[int, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT provider, source_slug
            FROM sources
            WHERE source_slug IS NOT NULL
            """
        )
        existing_keys = {(row[0], row[1]) for row in cur.fetchall()}
        cur.executemany(
            UPSERT_SOURCES_SQL,
            [
                (
                    candidate.provider,
                    candidate.source_slug,
                    candidate.canonical_url,
                    candidate.board_id,
                )
                for candidate in candidates
            ],
        )

    conn.commit()
    inserted = sum(
        (candidate.provider, candidate.source_slug) not in existing_keys
        for candidate in candidates
    )
    return inserted, len(candidates) - inserted


def build_report(
    candidates: list[SourceCandidate],
    *,
    csv_rows_read: int,
    parquet_rows_read: int,
    duplicates_merged: int,
    inserted: int,
    updated: int,
    sources_inserted: int,
    sources_updated: int,
    skipped: int,
    dry_run: bool,
) -> ImportReport:
    provider_counts = dict(sorted(Counter(c.provider for c in candidates).items()))
    csv_only = sum(candidate.origins == {"csv"} for candidate in candidates)
    parquet_only = sum(candidate.origins == {"parquet"} for candidate in candidates)
    overlapping = sum(candidate.origins == {"csv", "parquet"} for candidate in candidates)
    supported_pending = sum(
        candidate.provider in SUPPORTED_PROVIDERS for candidate in candidates
    )
    with_canonical_url = sum(candidate.canonical_url is not None for candidate in candidates)

    return ImportReport(
        csv_rows_read=csv_rows_read,
        parquet_rows_read=parquet_rows_read,
        normalized_candidates=len(candidates),
        duplicates_merged=duplicates_merged,
        inserted=inserted,
        updated=updated,
        sources_inserted=sources_inserted,
        sources_updated=sources_updated,
        skipped_invalid_missing_keys=skipped,
        provider_counts=provider_counts,
        csv_only=csv_only,
        parquet_only=parquet_only,
        overlapping=overlapping,
        supported_pending=supported_pending,
        unsupported_pending=len(candidates) - supported_pending,
        with_canonical_url=with_canonical_url,
        without_canonical_url=len(candidates) - with_canonical_url,
        dry_run=dry_run,
    )


def run_import(
    *,
    sources_csv: Path | None,
    companies_parquet: Path | None,
    dry_run: bool = False,
) -> ImportReport:
    csv_candidates: list[SourceCandidate] = []
    parquet_candidates: list[SourceCandidate] = []
    csv_rows_read = parquet_rows_read = skipped = 0

    if sources_csv is not None:
        csv_candidates, csv_rows_read, csv_skipped = load_csv_candidates(sources_csv)
        skipped += csv_skipped
    if companies_parquet is not None:
        parquet_candidates, parquet_rows_read, parquet_skipped = load_parquet_candidates(
            companies_parquet
        )
        skipped += parquet_skipped

    candidates, duplicates_merged = merge_candidates(csv_candidates, parquet_candidates)
    inserted = updated = sources_inserted = sources_updated = 0
    if not dry_run:
        with get_connection() as conn:
            inserted, updated = upsert_candidates(conn, candidates)
            sources_inserted, sources_updated = upsert_sources(conn, candidates)

    return build_report(
        candidates,
        csv_rows_read=csv_rows_read,
        parquet_rows_read=parquet_rows_read,
        duplicates_merged=duplicates_merged,
        inserted=inserted,
        updated=updated,
        sources_inserted=sources_inserted,
        sources_updated=sources_updated,
        skipped=skipped,
        dry_run=dry_run,
    )


def import_candidates(input_file: Path) -> int:
    """Backward-compatible CSV-only import entry point."""
    report = run_import(
        sources_csv=input_file,
        companies_parquet=None,
        dry_run=False,
    )
    return report.inserted


def print_report(report: ImportReport) -> None:
    print(f"CSV rows read: {report.csv_rows_read}")
    print(f"Parquet rows read: {report.parquet_rows_read}")
    print(f"Normalized candidates: {report.normalized_candidates}")
    print(f"Duplicates merged: {report.duplicates_merged}")
    suffix = " (dry run)" if report.dry_run else ""
    print(f"source_candidates inserted: {report.inserted}{suffix}")
    print(f"source_candidates updated: {report.updated}{suffix}")
    print(f"sources inserted: {report.sources_inserted}{suffix}")
    print(f"sources updated: {report.sources_updated}{suffix}")
    print(f"Skipped invalid/missing keys: {report.skipped_invalid_missing_keys}")
    print("By provider:")
    for provider, count in report.provider_counts.items():
        print(f"  {provider}: {count}")
    other = sum(
        count
        for provider, count in report.provider_counts.items()
        if provider not in REPORT_PROVIDERS
    )
    print(f"  other: {other}")
    print(f"CSV only: {report.csv_only}")
    print(f"Parquet only: {report.parquet_only}")
    print(f"Both: {report.overlapping}")
    print(f"Supported pending: {report.supported_pending}")
    print(f"Unsupported pending: {report.unsupported_pending}")
    print(f"With canonical_url: {report.with_canonical_url}")
    print(f"Without canonical_url: {report.without_canonical_url}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize and import CSV and Parquet source candidates into PostgreSQL."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Backward-compatible alias for --sources-csv.",
    )
    parser.add_argument("--sources-csv", type=Path)
    parser.add_argument("--companies-parquet", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read, normalize, merge, and report without writing to PostgreSQL.",
    )
    args = parser.parse_args()

    if args.input and args.sources_csv:
        parser.error("Use either --input or --sources-csv, not both.")

    sources_csv = args.sources_csv or args.input
    if sources_csv is None and args.companies_parquet is None:
        sources_csv = DEFAULT_INPUT

    configure_logging()
    report = run_import(
        sources_csv=sources_csv,
        companies_parquet=args.companies_parquet,
        dry_run=args.dry_run,
    )
    print_report(report)


if __name__ == "__main__":
    main()
