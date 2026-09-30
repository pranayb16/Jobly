from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    html: str | None = None
    text: str | None = None


class Job(BaseModel):
    external_job_id: str
    provider: str

    company: str | None = None
    title: str

    location: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None

    posted_at: datetime | None = None
    posted_at_source: str | None = None

    description: JobDescription = Field(
        default_factory=JobDescription
    )

    job_url: str | None = None
    apply_url: str | None = None

    raw: dict[str, Any] = Field(
        default_factory=dict
    )