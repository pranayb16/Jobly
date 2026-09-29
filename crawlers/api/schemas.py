from datetime import datetime

from pydantic import BaseModel


class JobListItem(BaseModel):
    id: int

    external_job_id: str
    provider: str

    company: str | None = None
    title: str

    location: str | None = None
    employment_type: str | None = None
    workplace_type: str | None = None

    posted_at: datetime | None = None
    posted_at_source: str | None = None

    job_url: str | None = None
    apply_url: str | None = None

    first_seen_at: datetime
    last_seen_at: datetime


class JobDetail(JobListItem):
    description_text: str | None = None
    description_html: str | None = None


class JobsResponse(BaseModel):
    count: int
    limit: int
    offset: int
    jobs: list[JobListItem]