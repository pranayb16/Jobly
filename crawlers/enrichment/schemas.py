from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from crawlers.enrichment.taxonomy import (
    SENIORITY_LEVELS,
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

    @field_validator(
        "job_family",
        "job_subfamily",
    )
    @classmethod
    def normalize_category(
        cls,
        value: str | None,
    ):

        if value is None:
            return None

        value = value.strip().lower()

        value = "_".join(
            value.replace("-", " ").split()
        )

        return value

    @field_validator("related_roles")
    @classmethod
    def normalize_roles(
        cls,
        values: list[str],
    ):

        if len(values) > 8:
            raise ValueError(
                "Maximum of 8 related roles"
            )

        normalized = []

        for value in values:

            value = value.strip().lower()

            value = "_".join(
                value.replace("-", " ").split()
            )

            if value and value not in normalized:
                normalized.append(value)

        return normalized

    @field_validator("seniority")
    @classmethod
    def validate_seniority(
        cls,
        value: str,
    ):

        value = value.strip().lower()

        aliases = {
            "mid-level": "mid",
            "mid_level": "mid",
            "junior": "entry",
            "entry-level": "entry",
            "entry_level": "entry",
            "sr": "senior",
            "sr.": "senior",
            "vp": "vp",
            "vice_president": "vp",
        }

        value = aliases.get(
            value,
            value,
        )

        if value not in SENIORITY_LEVELS:
            return "unknown"

        return value

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

JOB_CLASSIFICATION_JSON_SCHEMA = {
    "type": "object",

    "properties": {
        "job_family": {
        "type": "string",
    },

        "job_subfamily": {
            "anyOf": [
                {
                    "type": "string",
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
            },

            "maxItems": 8,
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