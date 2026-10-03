from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging
from jobly.sources.manager import extract_board_id, normalize_provider, normalize_url


DEFAULT_INPUT = Path(__file__).resolve().parents[3] / "data" / "cleaned" / "valid_sources.csv"


def import_candidates(input_file: Path) -> int:
    imported = 0
    with input_file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                provider = normalize_provider(row.get("ats_platform", ""))
                url = normalize_url(row.get("canonical_url", ""))
                if not provider or not url:
                    continue
                status = "valid" if row.get("status", "").strip().lower() == "valid" else "pending"
                company_name = (row.get("company_name") or row.get("company") or "").strip() or None
                cur.execute(
                    """
                    INSERT INTO source_candidates (
                        provider, canonical_url, board_id, company_name, status
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (provider, canonical_url) DO NOTHING
                    """,
                    (provider, url, extract_board_id(url), company_name, status),
                )
                imported += cur.rowcount
        conn.commit()
    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CSV source candidates into PostgreSQL.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    configure_logging()
    print(f"Imported {import_candidates(args.input)} source candidates")


if __name__ == "__main__":
    main()
