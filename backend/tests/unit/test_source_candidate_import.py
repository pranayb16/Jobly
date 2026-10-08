from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from jobly.commands.import_source_candidates import (
    UPSERT_SOURCES_SQL,
    UPSERT_SQL,
    SourceCandidate,
    build_report,
    load_csv_candidates,
    load_parquet_candidates,
    merge_candidates,
    upsert_candidates,
    upsert_sources,
)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ats_platform", "canonical_url", "company_name", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_parquet(path: Path, rows: list[tuple[object, ...]]) -> None:
    connection = duckdb.connect()
    try:
        connection.execute(
            """
            CREATE TABLE companies (
                ats VARCHAR,
                slug VARCHAR,
                name VARCHAR,
                career_url VARCHAR
            )
            """
        )
        connection.executemany(
            "INSERT INTO companies VALUES (?, ?, ?, ?)",
            rows,
        )
        connection.execute(
            "COPY companies TO ? (FORMAT PARQUET)",
            [str(path)],
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("provider", "url", "slug"),
    [
        ("greenhouse", "https://job-boards.greenhouse.io/databricks", "databricks"),
        ("ashby", "https://jobs.ashbyhq.com/plaid", "plaid"),
        ("lever", "https://jobs.lever.co/jobgether", "jobgether"),
    ],
)
def test_csv_supported_candidates_are_normalized_pending(
    tmp_path,
    provider,
    url,
    slug,
):
    path = tmp_path / "candidates.csv"
    write_csv(
        path,
        [
            {
                "ats_platform": provider.upper(),
                "canonical_url": url,
                "company_name": "Example",
                "status": "valid",
            }
        ],
    )

    candidates, rows_read, skipped = load_csv_candidates(path)

    assert rows_read == 1
    assert skipped == 0
    assert candidates == [
        SourceCandidate(
            provider=provider,
            source_slug=slug,
            canonical_url=url,
            company_name="Example",
            board_id=slug,
            origins=frozenset({"csv"}),
        )
    ]
    assert candidates[0].status == "pending"


def test_parquet_imports_supported_and_unsupported_rows_including_null_url(tmp_path):
    path = tmp_path / "companies.parquet"
    write_parquet(
        path,
        [
            ("ashbyhq", "plaid", "Plaid", "https://jobs.ashbyhq.com/plaid"),
            ("workday", "acme.wd1/jobs", "Acme", "https://acme.wd1.myworkdayjobs.com/jobs"),
            ("gem", "future-company", "Future Company", None),
        ],
    )

    candidates, rows_read, skipped = load_parquet_candidates(path)

    assert rows_read == 3
    assert skipped == 0
    by_key = {(candidate.provider, candidate.source_slug): candidate for candidate in candidates}
    assert by_key[("ashby", "plaid")].company_name == "Plaid"
    assert by_key[("ashby", "plaid")].canonical_url == "https://jobs.ashbyhq.com/plaid"
    assert by_key[("workday", "acme.wd1/jobs")].status == "pending"
    assert by_key[("gem", "future-company")].canonical_url is None
    assert by_key[("gem", "future-company")].status == "pending"


def test_csv_and_parquet_duplicates_use_required_field_precedence():
    csv_candidate = SourceCandidate(
        provider="greenhouse",
        source_slug="example",
        canonical_url="https://job-boards.greenhouse.io/example",
        company_name="CSV Name",
        board_id="example",
        origins=frozenset({"csv"}),
    )
    parquet_candidate = SourceCandidate(
        provider="greenhouse",
        source_slug="example",
        canonical_url="https://boards.greenhouse.io/example",
        company_name="Parquet Name",
        board_id="example",
        origins=frozenset({"parquet"}),
    )

    merged, duplicates = merge_candidates([csv_candidate], [parquet_candidate])

    assert duplicates == 1
    assert len(merged) == 1
    assert merged[0].canonical_url == csv_candidate.canonical_url
    assert merged[0].company_name == "Parquet Name"
    assert merged[0].origins == {"csv", "parquet"}


class RecordingCursor:
    def __init__(self, existing):
        self.existing = existing
        self.statements = []
        self.executemany_call = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, params=None):
        self.statements.append((" ".join(statement.split()), params))

    def fetchall(self):
        return self.existing

    def executemany(self, statement, params):
        self.executemany_call = (" ".join(statement.split()), list(params))


class RecordingConnection:
    def __init__(self, existing):
        self.cursor_instance = RecordingCursor(existing)
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_existing_database_candidate_is_upserted_without_duplication():
    connection = RecordingConnection(existing=[("greenhouse", "example")])
    candidate = SourceCandidate(
        provider="greenhouse",
        source_slug="example",
        canonical_url="https://job-boards.greenhouse.io/example",
        company_name="Filled Name",
        board_id="example",
    )

    inserted, updated = upsert_candidates(connection, [candidate])

    assert (inserted, updated) == (0, 1)
    assert connection.commits == 1
    sql, params = connection.cursor_instance.executemany_call
    assert "ON CONFLICT (provider, source_slug)" in sql
    assert "COALESCE( EXCLUDED.canonical_url, source_candidates.canonical_url )" in sql
    assert "COALESCE( EXCLUDED.company_name, source_candidates.company_name )" in sql
    assert params[0][2] == candidate.canonical_url
    assert params[0][4] == "Filled Name"


def test_source_inventory_upsert_defaults_new_rows_without_overwriting_status():
    connection = RecordingConnection(existing=[("greenhouse", "example")])
    candidates = [
        SourceCandidate(
            provider="greenhouse",
            source_slug="example",
            canonical_url="https://job-boards.greenhouse.io/example",
            company_name="Existing Active Source",
            board_id="example",
        ),
        SourceCandidate(
            provider="workday",
            source_slug="new-company",
            canonical_url="https://example.wd1.myworkdayjobs.com/jobs",
            company_name="New Source",
            board_id="new-company",
        ),
    ]

    inserted, updated = upsert_sources(connection, candidates)

    assert (inserted, updated) == (1, 1)
    assert connection.commits == 1
    sql, params = connection.cursor_instance.executemany_call
    assert "'not_verified'" in sql
    assert "ON CONFLICT (provider, source_slug)" in sql
    assert "status =" not in sql.split("DO UPDATE SET", 1)[1]
    assert params[1] == (
        "workday",
        "new-company",
        "https://example.wd1.myworkdayjobs.com/jobs",
        "new-company",
    )
    assert "'not_verified'" in UPSERT_SOURCES_SQL


def test_report_counts_origins_support_and_url_coverage():
    candidates = [
        SourceCandidate("greenhouse", "one", "https://example.test/one", None, "one", frozenset({"csv"})),
        SourceCandidate("workday", "two", None, "Two", "two", frozenset({"parquet"})),
        SourceCandidate("lever", "three", "https://example.test/three", "Three", "three", frozenset({"csv", "parquet"})),
    ]

    report = build_report(
        candidates,
        csv_rows_read=2,
        parquet_rows_read=2,
        duplicates_merged=1,
        inserted=0,
        updated=0,
        sources_inserted=0,
        sources_updated=0,
        skipped=0,
        dry_run=True,
    )

    assert report.csv_only == 1
    assert report.parquet_only == 1
    assert report.overlapping == 1
    assert report.supported_pending == 2
    assert report.unsupported_pending == 1
    assert report.with_canonical_url == 2
    assert report.without_canonical_url == 1
    assert "'pending'" in UPSERT_SQL
