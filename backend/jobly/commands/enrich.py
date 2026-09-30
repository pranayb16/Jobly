from jobly.enrichment.worker import main as worker_main
from jobly.logging_config import configure_logging


def main() -> None:
    configure_logging()
    worker_main()


if __name__ == "__main__":
    main()
