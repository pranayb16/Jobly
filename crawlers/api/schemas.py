from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
)


class AiLocation(BaseModel):
    city: str | None = None
    state: str | None = None
    state_code: str | None = None

    country: str | None = None
    country_code: str | None = None

    remote: bool = False


class JobListItem(BaseModel):
    id: int

    external_job_id: str
    provider: str

    company: str | None = None
    title: str

    location: str | None = None

    employment_type: str | None = None
    workplace_type: str | None = None

    description_excerpt: str | None = None

    posted_at: datetime | None = None
    posted_at_source: str | None = None

    job_url: str | None = None
    apply_url: str | None = None

    first_seen_at: datetime
    last_seen_at: datetime

    # -----------------------------
    # AI enrichment
    # -----------------------------

    job_family: str | None = None
    job_subfamily: str | None = None

    related_roles: list[str] = Field(
        default_factory=list
    )

    skills: list[str] = Field(
        default_factory=list
    )

    seniority: str | None = None

    years_experience_min: int | None = None
    years_experience_max: int | None = None

    ai_locations: list[AiLocation] = Field(
        default_factory=list
    )

    classification_confidence: float | None = None


class JobDetail(JobListItem):
    description_text: str | None = None
    description_html: str | None = None


class JobsResponse(BaseModel):
    count: int
    limit: int
    offset: int

    jobs: list[JobListItem]