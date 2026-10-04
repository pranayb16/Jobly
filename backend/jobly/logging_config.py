from __future__ import annotations

import logging
import sys

from jobly.config import (
    get_settings,
)


def configure_logging() -> None:

    settings = get_settings()


    logging.basicConfig(
        level=getattr(
            logging,
            settings.log_level,
            logging.INFO,
        ),
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        stream=sys.stdout,
        force=True,
    )


def enable_pipeline_database_logging() -> None:

    from jobly.observability.db_log_handler import (
        PipelineDatabaseLogHandler,
    )


    root = logging.getLogger()


    # Prevent duplicate handlers if called twice.

    if any(
        isinstance(
            handler,
            PipelineDatabaseLogHandler,
        )
        for handler in root.handlers
    ):
        return


    handler = (
        PipelineDatabaseLogHandler()
    )


    handler.setLevel(
        logging.INFO
    )


    root.addHandler(
        handler
    )