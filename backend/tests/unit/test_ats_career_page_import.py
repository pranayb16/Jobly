from __future__ import annotations

import csv

from jobly.commands.import_ats_career_page_urls import (
    InventorySource,
    load_inventory,
    source_slug_for_url,
    upsert_inventory,
)


def test_load_inventory_accepts_raw_two_column_csv_and_normalizes_aliases(tmp_path):
    path = tmp_path / "ats_career_page_urls.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["canonical_url", "ats_platform"])
        writer.writeheader()
        writer.writerows(
            [
                {
                    "canonical_url": "https://jobs.ashbyhq.com/example",
                    "ats_platform": "Ashby",
                },
                {
                    "canonical_url": "https://example.breezy.hr/",
                    "ats_platform": "Breezy HR",
                },
            ]
        )

    sources, rows_read, skipped = load_inventory(path)

    assert rows_read == 2
    assert skipped == 0
    assert {source.provider for source in sources} == {"ashby", "breezy"}


def test_url_hash_keeps_adp_sources_distinct():
    first, first_board = source_slug_for_url(
        "adp",
        "https://workforcenow.adp.com/jobs?cid=one",
    )
    second, second_board = source_slug_for_url(
        "adp",
        "https://workforcenow.adp.com/jobs?cid=two",
    )

    assert first.startswith("url_")
    assert second.startswith("url_")
    assert first != second
    assert first_board is None
    assert second_board is None


class RecordingCursor:
    def __init__(self, existing):
        self.existing = existing
        self.executemany_params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _statement, _params=None):
        return None

    def fetchall(self):
        return self.existing

    def executemany(self, statement, params):
        self.statement = " ".join(statement.split())
        self.executemany_params = list(params)


class RecordingConnection:
    def __init__(self, existing):
        self.cursor_instance = RecordingCursor(existing)
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_import_inserts_only_new_sources_as_not_verified_and_preserves_matches():
    existing_url = "https://jobs.ashbyhq.com/existing"
    connection = RecordingConnection(
        existing=[("ashby", "existing", existing_url)]
    )
    sources = [
        InventorySource("ashby", "existing", existing_url, "existing"),
        InventorySource(
            "ashby",
            "new",
            "https://jobs.ashbyhq.com/new",
            "new",
        ),
    ]

    inserted, matched = upsert_inventory(connection, sources)

    assert (inserted, matched) == (1, 1)
    assert connection.commits == 1
    assert "'not_verified'" in connection.cursor_instance.statement
    assert connection.cursor_instance.executemany_params == [
        ("ashby", "new", "https://jobs.ashbyhq.com/new", "new")
    ]
