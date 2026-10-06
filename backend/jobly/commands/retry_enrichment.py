from __future__ import annotations

import argparse

from jobly.db.connection import get_connection
from jobly.enrichment.worker import requeue_failed_enrichment
from jobly.logging_config import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Requeue failed enrichment rows after an outage is resolved."
    )
    parser.add_argument(
        "--include-permanent",
        action="store_true",
        help="Also retry failures classified as non-transient.",
    )
    args = parser.parse_args()

    configure_logging()
    with get_connection() as conn:
        updated = requeue_failed_enrichment(
            conn,
            include_permanent=args.include_permanent,
        )
    print(f"Requeued enrichment rows: {updated}")


if __name__ == "__main__":
    main()
