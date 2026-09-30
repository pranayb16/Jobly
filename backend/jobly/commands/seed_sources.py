import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

from jobly.db.connection import get_connection
from jobly.logging_config import configure_logging


DEFAULT_INPUT_FILE = Path(__file__).resolve().parents[3] / "data" / "cleaned" / "valid_sources.csv"


def extract_board_id(url: str) -> str | None:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[0] if parts else None


def seed_sources(input_file: Path) -> int:
    with input_file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                provider = row["ats_platform"].strip().lower()
                url = row["canonical_url"].strip()
                cur.execute(
                    """
                    INSERT INTO sources (provider, canonical_url, board_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (provider, canonical_url) DO NOTHING
                    """,
                    (provider, url, extract_board_id(url)),
                )
        conn.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed verified ATS sources into PostgreSQL.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    args = parser.parse_args()
    configure_logging()
    count = seed_sources(args.input)
    print(f"Loaded {count} verified sources")


if __name__ == "__main__":
    main()
