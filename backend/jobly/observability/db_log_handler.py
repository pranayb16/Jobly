from __future__ import annotations

import logging
import sys
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


            with get_connection() as conn:

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

            # Never log this through logging itself,
            # otherwise we could recurse forever.

            try:
                sys.stderr.write(
                    "Pipeline DB log handler "
                    f"failed: {exc}\n"
                )

            except Exception:
                pass