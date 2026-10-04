from __future__ import annotations

import argparse

from jobly.intelligence.hiring_stats import (
    refresh_hiring_stats,
)

from jobly.logging_config import (
    configure_logging,
)


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Refresh deterministic company "
            "hiring statistics."
        )
    )


    parser.add_argument(
        "--company-id",
        type=int,
        default=None,
        help=(
            "Refresh one company only. "
            "Omit to refresh all companies."
        ),
    )


    args = parser.parse_args()


    if (
        args.company_id is not None
        and args.company_id < 1
    ):
        parser.error(
            "--company-id must be at least 1"
        )


    configure_logging()


    summary = refresh_hiring_stats(
        company_id=args.company_id
    )


    print(
        "Hiring stats complete | "
        f"refreshed="
        f"{summary.companies_refreshed} | "
        f"publishable="
        f"{summary.publishable_companies} | "
        f"unpublishable="
        f"{summary.unpublishable_companies}"
    )


if __name__ == "__main__":
    main()