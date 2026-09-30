import argparse
import logging
import subprocess
import sys
import time

from jobly.logging_config import configure_logging


logger = logging.getLogger(__name__)


def _run(command: list[str], name: str) -> None:
    logger.info("pipeline_stage_start stage=%s", name)
    started = time.monotonic()
    result = subprocess.run(command, check=False)
    duration = time.monotonic() - started
    if result.returncode:
        logger.error(
            "pipeline_stage_failed stage=%s status=failed exit_code=%s duration=%.2f",
            name,
            result.returncode,
            duration,
        )
        raise SystemExit(result.returncode)
    logger.info("pipeline_stage_complete stage=%s status=success duration=%.2f", name, duration)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run crawl, then enrichment, once.")
    parser.add_argument("--enrichment-limit", type=int, default=10)
    args = parser.parse_args()
    if args.enrichment_limit < 1:
        parser.error("--enrichment-limit must be at least 1")
    configure_logging()
    started = time.monotonic()
    logger.info("pipeline_start")
    _run([sys.executable, "-m", "jobly.commands.crawl"], "crawl")
    _run(
        [sys.executable, "-m", "jobly.commands.enrich", "--limit", str(args.enrichment_limit)],
        "enrich",
    )
    logger.info("pipeline_complete status=success duration=%.2f", time.monotonic() - started)


if __name__ == "__main__":
    main()
