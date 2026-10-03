from __future__ import annotations

import argparse
from datetime import date

from jobly.intelligence.snapshots import build_snapshots
from jobly.logging_config import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Build idempotent daily company snapshots.")
    parser.add_argument("--date", type=date.fromisoformat, default=None)
    args = parser.parse_args()
    configure_logging()
    summary = build_snapshots(args.date)
    print(
        f"Snapshot complete | date={summary.snapshot_date} | "
        f"companies={summary.snapshots_created}"
    )


if __name__ == "__main__":
    main()
