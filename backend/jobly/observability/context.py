from __future__ import annotations

from contextvars import ContextVar


pipeline_run_id_context: ContextVar[
    int | None
] = ContextVar(
    "pipeline_run_id",
    default=None,
)


pipeline_stage_context: ContextVar[
    str | None
] = ContextVar(
    "pipeline_stage",
    default=None,
)


def set_pipeline_run_id(
    pipeline_run_id: int | None,
) -> None:

    pipeline_run_id_context.set(
        pipeline_run_id
    )


def set_pipeline_stage(
    stage: str | None,
) -> None:

    pipeline_stage_context.set(
        stage
    )


def get_pipeline_run_id() -> int | None:

    return pipeline_run_id_context.get()


def get_pipeline_stage() -> str | None:

    return pipeline_stage_context.get()