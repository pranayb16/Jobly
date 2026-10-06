from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


Seniority = Literal[
    "intern",
    "entry",
    "mid",
    "senior",
    "staff",
    "principal",
    "director",
    "vp",
    "executive",
    "unknown",
]


SkillRequirement = Literal[
    "required",
    "preferred",
    "mentioned",
]


CertificationRequirement = Literal[
    "required",
    "preferred",
]

class SkillEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    name: str

    requirement: SkillRequirement


    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:

        cleaned = " ".join(
            value.strip().split()
        )

        if not cleaned:
            raise ValueError(
                "Skill name cannot be empty"
            )

        if cleaned.lower() in {
            "required",
            "preferred",
            "mentioned",
        }:
            raise ValueError(
                "Skill name must be an actual skill"
            )

        return cleaned


class CertificationEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    name: str

    requirement: CertificationRequirement


    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:

        cleaned = " ".join(
            value.strip().split()
        )

        if not cleaned:
            raise ValueError(
                "Certification name cannot be empty"
            )

        return cleaned


EducationLevel = Literal[
    "none",
    "high_school",
    "associate",
    "bachelor",
    "master",
    "doctorate",
    "professional",
    "unknown",
]


WorkplaceType = Literal[
    "remote",
    "hybrid",
    "onsite",
    "flexible",
    "unknown",
]


EmploymentType = Literal[
    "full_time",
    "part_time",
    "contract",
    "temporary",
    "internship",
    "seasonal",
    "unknown",
]


SalaryPeriod = Literal[
    "hour",
    "day",
    "week",
    "month",
    "year",
    "unknown",
]


VisaSponsorship = Literal[
    "available",
    "not_available",
    "unknown",
]


class EnrichedLocationV3(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    city: str | None
    # Example: "Austin"

    state: str | None
    # Example: "Texas"

    state_code: str | None
    # Example: "TX"

    country: str | None
    # Example: "United States"

    country_code: str | None
    # Example: "US"


class JobEnrichmentV3(BaseModel):
    """
    Compact semantic enrichment with an explicit absence contract.

    Every top-level key is required. Nullable fields use null and
    collection fields use an explicit empty list when the posting
    contains no supported evidence for that dimension.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    # ========================================================
    # ROLE
    # ========================================================

    standardized_title: str | None
    # Example: "Senior Backend Engineer"

    job_family: str | None
    # Example: "software_engineering"

    job_subfamily: str | None
    # Example: "backend_engineering"

    # related_roles: list[str] = Field(
    #     default_factory=list
    # )
    # Example:
    # ["Backend Engineer", "Platform Engineer"]

    seniority: Seniority
    # Example: "senior"


    # ========================================================
    # SKILLS
    # ========================================================

    skills: list[SkillEntry]
    # Example:
    # {
    #     "Python": "required",
    #     "SQL": "required",
    #     "AWS": "preferred",
    #     "Kubernetes": "mentioned"
    # }

    domain_tags: list[str]
    # Example:
    # ["fintech", "payments"]


    # ========================================================
    # EXPERIENCE
    # ========================================================

    years_experience_min: int | None = Field(
        ...,
        ge=0,
        le=80,
    )
    # Example:
    # "3+ years experience" -> 3

    years_experience_max: int | None = Field(
        ...,
        ge=0,
        le=80,
    )
    # Example:
    # "3-5 years experience" -> 5


    # ========================================================
    # EDUCATION
    # ========================================================

    education_level: EducationLevel
    # Example: "bachelor"

    education_fields: list[str]
    # Example:
    # ["Computer Science", "Engineering"]

    certifications: list[CertificationEntry]
    # Example:
    # {
    #     "CPA": "required",
    #     "CFA": "preferred"
    # }


    # ========================================================
    # LOCATION / WORK ARRANGEMENT
    # ========================================================

    locations: list[EnrichedLocationV3]
    # Example:
    # [
    #     {
    #         "city": "Austin",
    #         "state": "Texas",
    #         "state_code": "TX",
    #         "country": "United States",
    #         "country_code": "US"
    #     }
    # ]

    workplace_type: WorkplaceType
    # Example: "hybrid"

    # remote_scope: RemoteScope = "unknown"
    # # Example: "country"

    # relocation_available: bool | None = None
    # # Example: True


    # ========================================================
    # EMPLOYMENT
    # ========================================================

    employment_type: EmploymentType
    # Example: "full_time"

    contract_duration: str | None
    # Example: "12 months"


    # ========================================================
    # COMPENSATION
    # ========================================================

    salary_min: float | None = Field(
        ...,
        ge=0,
    )
    # Example: 120000

    salary_max: float | None = Field(
        ...,
        ge=0,
    )
    # Example: 160000

    salary_currency: str | None
    # Example: "USD"

    salary_period: SalaryPeriod
    # Example: "year"

    # salary_text: str | None = None
    # # Example: "$120,000-$160,000 annually"

    # bonus_available: bool | None = None
    # # Example: True

    # commission_available: bool | None = None
    # # Example: False

    # equity_available: bool | None = None
    # # Example: True

    # signing_bonus_available: bool | None = None
    # # Example: False

    # ote_min: float | None = Field(
    #     default=None,
    #     ge=0,
    # )
    # # Example: 180000

    # ote_max: float | None = Field(
    #     default=None,
    #     ge=0,
    # )
    # # Example: 220000


    # ========================================================
    # VISA / AUTHORIZATION / SECURITY
    # ========================================================

    visa_sponsorship: VisaSponsorship
    # Example: "available"

    work_authorization_required: bool | None
    # Example: True

    citizenship_requirement: str | None
    # Example: "U.S. citizen"

    security_clearance_required: bool | None
    # Example: True

    security_clearance_level: str | None
    # Example: "TS/SCI"


    # ========================================================
    # ORGANIZATION
    # ========================================================

    offices: list[str]
    # Example:
    # ["Austin", "New York"]


    # ========================================================
    # QUALITY
    # ========================================================

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    # Example: 0.91


    @field_validator(
        "domain_tags",
        "education_fields",
        "offices",
    )
    @classmethod
    def clean_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        result: list[str] = []

        for value in values:
            cleaned = " ".join(
                value.strip().split()
            )

            if (
                cleaned
                and cleaned not in result
            ):
                result.append(
                    cleaned
                )

        return result


    @model_validator(mode="after")
    def validate_ranges(
        self,
    ):
        ranges = (
            (
                self.years_experience_min,
                self.years_experience_max,
                "years_experience",
            ),
            (
                self.salary_min,
                self.salary_max,
                "salary",
            ),
            # (
            #     self.ote_min,
            #     self.ote_max,
            #     "ote",
            # ),
        )

        for low, high, name in ranges:
            if (
                low is not None
                and high is not None
                and low > high
            ):
                raise ValueError(
                    f"{name} minimum cannot exceed maximum"
                )

        aliases = {
            "js": "JavaScript",
            "javascript": "JavaScript",
            "nodejs": "Node.js",
            "node.js": "Node.js",
            "postgres": "PostgreSQL",
            "postgresql": "PostgreSQL",
        }
        rank = {"mentioned": 0, "preferred": 1, "required": 2}
        merged: dict[str, SkillEntry] = {}
        for skill in self.skills:
            canonical = aliases.get(skill.name.casefold(), skill.name)
            key = "".join(character for character in canonical.casefold() if character.isalnum())
            existing = merged.get(key)
            if existing is None or rank[skill.requirement] > rank[existing.requirement]:
                merged[key] = SkillEntry(name=canonical, requirement=skill.requirement)
        self.skills = list(merged.values())

        certification_rank = {"preferred": 0, "required": 1}
        certifications: dict[str, CertificationEntry] = {}
        for certification in self.certifications:
            key = " ".join(certification.name.casefold().split())
            existing = certifications.get(key)
            if existing is None or certification_rank[certification.requirement] > certification_rank[existing.requirement]:
                certifications[key] = certification
        self.certifications = list(certifications.values())
        return self


JOB_ENRICHMENT_V3_JSON_SCHEMA = (
    JobEnrichmentV3.model_json_schema()
)
