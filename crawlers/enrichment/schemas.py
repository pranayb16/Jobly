from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from crawlers.enrichment.taxonomy import (
    ALL_SUBFAMILIES,
    JOB_FAMILIES,
    RELATED_ROLES,
    SENIORITY_LEVELS,
    SUBFAMILIES_BY_FAMILY,
)


class ExtractedLocation(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    city: str | None
    state: str | None
    state_code: str | None

    country: str | None
    country_code: str | None

    remote: bool


class JobClassification(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    job_family: str

    job_subfamily: str | None

    related_roles: list[str]

    skills: list[str]

    seniority: str

    years_experience_min: int | None
    years_experience_max: int | None

    additional_locations: list[ExtractedLocation]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    @field_validator("job_family")
    @classmethod
    def validate_family(cls, value: str):
        if value not in JOB_FAMILIES:
            raise ValueError(
                f"Unsupported job family: {value}"
            )

        return value

    @field_validator("seniority")
    @classmethod
    def validate_seniority(cls, value: str):
        if value not in SENIORITY_LEVELS:
            raise ValueError(
                f"Unsupported seniority: {value}"
            )

        return value

    @field_validator("related_roles")
    @classmethod
    def validate_related_roles(
        cls,
        values: list[str],
    ):
        if len(values) > 6:
            raise ValueError(
                "Maximum of 6 related roles"
            )

        invalid = [
            role
            for role in values
            if role not in RELATED_ROLES
        ]

        if invalid:
            raise ValueError(
                f"Unsupported roles: {invalid}"
            )

        # Deduplicate while preserving order.
        return list(dict.fromkeys(values))

    @field_validator("skills")
    @classmethod
    def clean_skills(
        cls,
        values: list[str],
    ):
        cleaned = []

        for skill in values:

            skill = skill.strip()

            if not skill:
                continue

            if skill not in cleaned:
                cleaned.append(skill)

        return cleaned

    @model_validator(mode="after")
    def validate_subfamily(self):

        if self.job_subfamily is None:
            return self

        if self.job_subfamily not in ALL_SUBFAMILIES:
            raise ValueError(
                "Unsupported job subfamily"
            )

        allowed = SUBFAMILIES_BY_FAMILY.get(
            self.job_family,
            [],
        )

        if self.job_subfamily not in allowed:
            raise ValueError(
                (
                    f"{self.job_subfamily} does not "
                    f"belong to {self.job_family}"
                )
            )

        return self

JOB_CLASSIFICATION_JSON_SCHEMA = {
    "type": "object",

    "properties": {
        "job_family": {
            "type": "string",
            "enum": JOB_FAMILIES,
        },

        "job_subfamily": {
            "anyOf": [
                {
                    "type": "string",
                    "enum": ALL_SUBFAMILIES,
                },
                {
                    "type": "null",
                },
            ]
        },

        "related_roles": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": RELATED_ROLES,
            },
        },

        "skills": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "seniority": {
            "type": "string",
            "enum": SENIORITY_LEVELS,
        },

        "years_experience_min": {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"},
            ]
        },

        "years_experience_max": {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"},
            ]
        },

        "additional_locations": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {
                    "city": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },

                    "state": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },

                    "state_code": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },

                    "country": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },

                    "country_code": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ]
                    },

                    "remote": {
                        "type": "boolean",
                    },
                },

                "required": [
                    "city",
                    "state",
                    "state_code",
                    "country",
                    "country_code",
                    "remote",
                ],

                "additionalProperties": False,
            },
        },

        "confidence": {
            "type": "number",
        },
    },

    "required": [
        "job_family",
        "job_subfamily",
        "related_roles",
        "skills",
        "seniority",
        "years_experience_min",
        "years_experience_max",
        "additional_locations",
        "confidence",
    ],

    "additionalProperties": False,
}