import argparse

from jobly.crawling.worker import run_crawl
from jobly.logging_config import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl active ATS sources once and exit.")
    parser.add_argument(
        "--source-limit", type=int, default=None, help="Override CRAWL_SOURCE_LIMIT for this run."
    )
    args = parser.parse_args()
    if args.source_limit is not None and args.source_limit < 1:
        parser.error("--source-limit must be at least 1")
    configure_logging()
    run_crawl(args.source_limit)


if __name__ == "__main__":
    main()
