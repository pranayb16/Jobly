from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CanonicalLocation(BaseModel):
    city: str | None = None

    state: str | None = None

    state_code: str | None = None

    country: str | None = None

    country_code: str | None = None


class CanonicalJob(BaseModel):
    # ---------------------------------------------------------
    # Identity
    # ---------------------------------------------------------

    job_id: int

    external_job_id: str

    source_id: int

    provider: str

    company_name: str | None = None

    original_title: str

    standardized_title: str | None = None

    job_url: str | None = None

    apply_url: str | None = None

    # ---------------------------------------------------------
    # Timing
    # ---------------------------------------------------------

    posted_at: datetime | None = None

    posted_at_source: str | None = None

    first_seen_at: datetime

    last_seen_at: datetime

    removed_at: datetime | None = None

    active: bool

    observed_new_after: datetime | None = None

    observed_new_before: datetime | None = None

    freshness_hours: float

    freshness_source: str

    last_verified_at: datetime

    job_age_bucket: str

    # ---------------------------------------------------------
    # Role
    # ---------------------------------------------------------

    job_family: str | None = None

    job_subfamily: str | None = None

    related_roles: list[str] = Field(
        default_factory=list
    )

    role_track: str | None = None

    seniority: str | None = None

    leadership_level: str | None = None

    role_keywords: list[str] = Field(
        default_factory=list
    )

    responsibility_tags: list[str] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Skills
    # ---------------------------------------------------------

    skills: list[str] = Field(
        default_factory=list
    )

    required_skills: list[str] = Field(
        default_factory=list
    )

    preferred_skills: list[str] = Field(
        default_factory=list
    )

    soft_skills: list[str] = Field(
        default_factory=list
    )

    skill_count: int = 0

    # ---------------------------------------------------------
    # Experience
    # ---------------------------------------------------------

    years_experience_min: int | None = None

    years_experience_max: int | None = None

    # ---------------------------------------------------------
    # Education / certifications
    # ---------------------------------------------------------

    education_required: str | None = None

    education_preferred: str | None = None

    education_level: str | None = None

    education_fields: list[str] = Field(
        default_factory=list
    )

    certifications: list[str] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    location: str | None = None

    locations: list[CanonicalLocation] = Field(
        default_factory=list
    )

    preferred_locations: list[
        CanonicalLocation
    ] = Field(
        default_factory=list
    )

    city: str | None = None

    state: str | None = None

    state_code: str | None = None

    country: str | None = None

    country_code: str | None = None

    workplace_type: str | None = None

    relocation_available: bool | None = None

    # ---------------------------------------------------------
    # Employment
    # ---------------------------------------------------------

    employment_type: str | None = None

    # ---------------------------------------------------------
    # Compensation
    # ---------------------------------------------------------

    salary_min: float | None = None

    salary_max: float | None = None

    salary_currency: str | None = None

    salary_period: str | None = None

    # ---------------------------------------------------------
    # Authorization / security
    # ---------------------------------------------------------

    visa_sponsorship: str | None = None

    work_authorization_required: bool | None = None

    citizenship_requirement: str | None = None

    security_clearance_required: bool | None = None

    security_clearance_level: str | None = None

    # ---------------------------------------------------------
    # Historical intelligence
    # ---------------------------------------------------------

    version_count: int = 1

    last_changed_at: datetime | None = None

    title_changed: bool = False

    location_changed: bool = False

    salary_changed: bool | None = None

    days_active: int = 0

    # ---------------------------------------------------------
    # AI metadata
    # ---------------------------------------------------------

    classification_confidence: float | None = None