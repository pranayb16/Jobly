from __future__ import annotations

from pydantic import BaseModel, Field

from jobly.jobs.schemas import (
    CanonicalJob,
    CanonicalLocation,
)


class JobListItem(
    CanonicalJob,
):
    """
    Canonical job plus temporary compatibility fields
    used by the existing /jobs frontend.
    """

    id: int

    company: str | None = None

    title: str

    description_excerpt: str | None = None

    ai_locations: list[
        CanonicalLocation
    ] = Field(
        default_factory=list
    )


class JobDetail(
    JobListItem,
):
    description_text: str | None = None

    description_html: str | None = None


class JobsResponse(
    BaseModel,
):
    count: int

    limit: int

    offset: int

    jobs: list[
        JobListItem
    ]