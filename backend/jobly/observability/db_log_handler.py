from __future__ import annotations

import logging
import sys
import threading
import traceback

from jobly.db.connection import (
    get_connection,
)

from jobly.observability.context import (
    get_pipeline_run_id,
    get_pipeline_stage,
)


class PipelineDatabaseLogHandler(
    logging.Handler
):
    def __init__(self) -> None:
        super().__init__()
        self._conn = None
        self._lock = threading.Lock()

    def _connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = get_connection()
        return self._conn

    def emit(
        self,
        record: logging.LogRecord,
    ) -> None:

        pipeline_run_id = (
            get_pipeline_run_id()
        )

        if pipeline_run_id is None:
            return

        try:

            message = (
                record.getMessage()
            )

            exception_text = None

            if record.exc_info:

                exception_text = "".join(
                    traceback.format_exception(
                        *record.exc_info
                    )
                )

            with self._lock:
                conn = self._connection()

                with conn.cursor() as cur:

                    cur.execute(
                        """
                        INSERT INTO pipeline_logs (
                            pipeline_run_id,
                            stage,
                            level,
                            logger,
                            message,
                            exception
                        )

                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        """,
                        (
                            pipeline_run_id,

                            get_pipeline_stage(),

                            record.levelname,

                            record.name,

                            message[:10000],

                            (
                                exception_text[
                                    :20000
                                ]
                                if exception_text
                                else None
                            ),
                        ),
                    )

                conn.commit()

        except Exception as exc:
            if self._conn is not None:
                try:
                    self._conn.rollback()
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

            # Never use logging here.
            # Doing so could recursively call this handler.

            try:

                sys.stderr.write(
                    "Pipeline DB log handler "
                    f"failed: {exc}\n"
                )

            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None
        super().close()
