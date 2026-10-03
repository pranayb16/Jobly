from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Seniority = Literal[
    "intern", "entry", "mid", "senior", "staff", "principal", "director", "vp", "executive", "unknown"
]
RoleTrack = Literal["individual_contributor", "management", "executive", "mixed", "unknown"]
LeadershipLevel = Literal["none", "lead", "manager", "director", "vp", "executive", "unknown"]
WorkplaceType = Literal["remote", "hybrid", "onsite", "flexible", "unknown"]
EmploymentType = Literal[
    "full_time", "part_time", "contract", "temporary", "internship", "seasonal", "unknown"
]
ScheduleType = Literal["standard", "shift", "flexible", "weekend", "night", "unknown"]
SalaryPeriod = Literal["hour", "day", "week", "month", "year", "unknown"]
Requirement = Literal["required", "preferred", "not_required", "unknown"]
EducationLevel = Literal[
    "high_school", "associate", "bachelor", "master", "doctorate", "professional", "unknown"
]
RemoteScope = Literal[
    "global", "country", "region", "state", "city", "time_zone", "not_remote", "unknown"
]


class EnrichedLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None


class JobEnrichmentV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standardized_title: str | None = None
    job_family: str | None = None
    job_subfamily: str | None = None
    related_roles: list[str] = Field(default_factory=list)
    role_track: RoleTrack = "unknown"
    seniority: Seniority = "unknown"
    leadership_level: LeadershipLevel = "unknown"
    people_management: bool | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_platforms: list[str] = Field(default_factory=list)
    devops_tools: list[str] = Field(default_factory=list)
    data_tools: list[str] = Field(default_factory=list)
    ml_ai_tools: list[str] = Field(default_factory=list)
    analytics_tools: list[str] = Field(default_factory=list)
    product_tools: list[str] = Field(default_factory=list)
    crm_tools: list[str] = Field(default_factory=list)
    security_tools: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    architecture_patterns: list[str] = Field(default_factory=list)
    platform_domains: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    responsibility_tags: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    years_experience_min: int | None = Field(default=None, ge=0, le=80)
    years_experience_max: int | None = Field(default=None, ge=0, le=80)
    management_experience_required: bool | None = None
    management_years_min: int | None = Field(default=None, ge=0, le=80)
    industry_experience_required: bool | None = None
    education_required: Requirement = "unknown"
    education_preferred: Requirement = "unknown"
    education_level: EducationLevel = "unknown"
    education_fields: list[str] = Field(default_factory=list)
    equivalent_experience_allowed: bool | None = None
    required_certifications: list[str] = Field(default_factory=list)
    preferred_certifications: list[str] = Field(default_factory=list)
    professional_license_required: bool | None = None
    locations: list[EnrichedLocation] = Field(default_factory=list)
    workplace_type: WorkplaceType = "unknown"
    remote_scope: RemoteScope = "unknown"
    relocation_available: bool | None = None
    employment_type: EmploymentType = "unknown"
    schedule_type: ScheduleType = "unknown"
    contract_duration: str | None = None
    travel_required: bool | None = None
    travel_percentage: int | None = Field(default=None, ge=0, le=100)
    on_call_required: bool | None = None
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    salary_period: SalaryPeriod = "unknown"
    salary_text: str | None = None
    bonus_available: bool | None = None
    commission_available: bool | None = None
    equity_available: bool | None = None
    signing_bonus_available: bool | None = None
    ote_min: float | None = Field(default=None, ge=0)
    ote_max: float | None = Field(default=None, ge=0)
    visa_sponsorship: Requirement = "unknown"
    work_authorization_required: bool | None = None
    citizenship_requirement: str | None = None
    security_clearance_required: bool | None = None
    security_clearance_level: str | None = None
    export_control_restriction: bool | None = None
    departments: list[str] = Field(default_factory=list)
    teams: list[str] = Field(default_factory=list)
    offices: list[str] = Field(default_factory=list)
    business_function: str | None = None
    product_area: str | None = None
    required_languages: list[str] = Field(default_factory=list)
    preferred_languages: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def require_every_dimension(cls, value):
        if isinstance(value, dict):
            missing = set(cls.model_fields) - set(value)
            if missing:
                raise ValueError(f"missing enrichment dimensions: {sorted(missing)}")
        return value

    @field_validator(
        "related_roles", "required_skills", "preferred_skills", "programming_languages",
        "frameworks", "databases", "cloud_platforms", "devops_tools", "data_tools",
        "ml_ai_tools", "analytics_tools", "product_tools", "crm_tools", "security_tools",
        "methodologies", "architecture_patterns", "platform_domains", "soft_skills",
        "responsibility_tags", "domain_tags", "education_fields", "required_certifications",
        "preferred_certifications", "departments", "teams", "offices", "required_languages",
        "preferred_languages", "benefits",
    )
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            cleaned = " ".join(value.strip().split())
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result

    @model_validator(mode="after")
    def validate_ranges(self):
        for low_name, high_name in (
            ("years_experience_min", "years_experience_max"),
            ("salary_min", "salary_max"),
            ("ote_min", "ote_max"),
        ):
            low = getattr(self, low_name)
            high = getattr(self, high_name)
            if low is not None and high is not None and low > high:
                raise ValueError(f"{low_name} cannot exceed {high_name}")
        return self


JOB_ENRICHMENT_V2_JSON_SCHEMA = JobEnrichmentV2.model_json_schema()
JOB_ENRICHMENT_V2_JSON_SCHEMA["required"] = list(
    JOB_ENRICHMENT_V2_JSON_SCHEMA["properties"]
)
