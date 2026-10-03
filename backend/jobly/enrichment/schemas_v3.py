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


RemoteScope = Literal[
    "global",
    "country",
    "region",
    "state",
    "city",
    "time_zone",
    "not_remote",
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

    city: str | None = None
    # Example: "Austin"

    state: str | None = None
    # Example: "Texas"

    state_code: str | None = None
    # Example: "TX"

    country: str | None = None
    # Example: "United States"

    country_code: str | None = None
    # Example: "US"


class JobEnrichmentV3(BaseModel):
    """
    Compact semantic enrichment.

    All fields except confidence are optional so Gemini can omit
    unsupported dimensions instead of spending output tokens on
    nulls, "unknown" values, and empty arrays.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    # ========================================================
    # ROLE
    # ========================================================

    standardized_title: str | None = None
    # Example: "Senior Backend Engineer"

    job_family: str | None = None
    # Example: "software_engineering"

    job_subfamily: str | None = None
    # Example: "backend_engineering"

    # related_roles: list[str] = Field(
    #     default_factory=list
    # )
    # Example:
    # ["Backend Engineer", "Platform Engineer"]

    seniority: Seniority = "unknown"
    # Example: "senior"


    # ========================================================
    # SKILLS
    # ========================================================

    skills: dict[
        str,
        SkillRequirement,
    ]
    # Example:
    # {
    #     "Python": "required",
    #     "SQL": "required",
    #     "AWS": "preferred",
    #     "Kubernetes": "mentioned"
    # }

    domain_tags: list[str] = Field(
        default_factory=list
    )
    # Example:
    # ["fintech", "payments"]


    # ========================================================
    # EXPERIENCE
    # ========================================================

    years_experience_min: int | None = Field(
        default=None,
        ge=0,
        le=80,
    )
    # Example:
    # "3+ years experience" -> 3

    years_experience_max: int | None = Field(
        default=None,
        ge=0,
        le=80,
    )
    # Example:
    # "3-5 years experience" -> 5


    # ========================================================
    # EDUCATION
    # ========================================================

    education_level: EducationLevel = "unknown"
    # Example: "bachelor"

    education_fields: list[str] = Field(
        default_factory=list
    )
    # Example:
    # ["Computer Science", "Engineering"]

    certifications: dict[
        str,
        CertificationRequirement,
    ] = Field(
        default_factory=dict
    )
    # Example:
    # {
    #     "CPA": "required",
    #     "CFA": "preferred"
    # }


    # ========================================================
    # LOCATION / WORK ARRANGEMENT
    # ========================================================

    locations: list[
        EnrichedLocationV3
    ] = Field(
        default_factory=list
    )
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

    workplace_type: WorkplaceType = "unknown"
    # Example: "hybrid"

    # remote_scope: RemoteScope = "unknown"
    # # Example: "country"

    # relocation_available: bool | None = None
    # # Example: True


    # ========================================================
    # EMPLOYMENT
    # ========================================================

    employment_type: EmploymentType = "unknown"
    # Example: "full_time"

    contract_duration: str | None = None
    # Example: "12 months"


    # ========================================================
    # COMPENSATION
    # ========================================================

    salary_min: float | None = Field(
        default=None,
        ge=0,
    )
    # Example: 120000

    salary_max: float | None = Field(
        default=None,
        ge=0,
    )
    # Example: 160000

    salary_currency: str | None = None
    # Example: "USD"

    salary_period: SalaryPeriod = "unknown"
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

    visa_sponsorship: VisaSponsorship = "unknown"
    # Example: "available"

    work_authorization_required: bool | None = None
    # Example: True

    citizenship_requirement: str | None = None
    # Example: "U.S. citizen"

    security_clearance_required: bool | None = None
    # Example: True

    security_clearance_level: str | None = None
    # Example: "TS/SCI"


    # ========================================================
    # ORGANIZATION
    # ========================================================

    offices: list[str] = Field(
        default_factory=list
    )
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


    @field_validator(
        "skills",
        "certifications",
    )
    @classmethod
    def clean_mappings(
        cls,
        values: dict,
    ) -> dict:
        result = {}

        for name, requirement in values.items():
            cleaned = " ".join(
                name.strip().split()
            )

            if cleaned:
                result[cleaned] = requirement

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

        return self


JOB_ENRICHMENT_V3_JSON_SCHEMA = (
    JobEnrichmentV3.model_json_schema()
)