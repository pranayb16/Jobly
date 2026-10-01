import argparse

from jobly.config import (
    get_settings,
)
from jobly.logging_config import (
    configure_logging,
)
from jobly.sources.manager import (
    ensure_source_target,
)


def main() -> None:

    settings = get_settings()

    parser = argparse.ArgumentParser(
        description=(
            "Ensure PostgreSQL contains "
            "the requested number of "
            "validated active ATS sources."
        )
    )

    parser.add_argument(
        "--target",
        type=int,
        default=(
            settings.crawl_source_limit
        ),
    )

    args = parser.parse_args()


    if args.target is None:

        parser.error(
            (
                "No source target configured. "
                "Set CRAWL_SOURCE_LIMIT or "
                "pass --target."
            )
        )


    if args.target < 1:

        parser.error(
            "--target must be at least 1"
        )


    configure_logging()


    summary = (
        ensure_source_target(
            args.target
        )
    )


    print(
        (
            "Source sync complete | "
            f"target={summary.target} | "
            f"before={summary.active_before} | "
            f"after={summary.active_after} | "
            f"added={summary.added} | "
            f"rejected={summary.rejected}"
        )
    )


if __name__ == "__main__":
    main()