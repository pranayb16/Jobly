import pytest
from pydantic import ValidationError

from jobly.enrichment.schemas_v3 import (
    JOB_ENRICHMENT_V3_JSON_SCHEMA,
    JobEnrichmentV3,
)
from jobly.enrichment.worker import _merge_trusted_ats_facts


def complete_v3_payload(**overrides):
    payload = {
        "standardized_title": None,
        "job_family": None,
        "job_subfamily": None,
        "seniority": "unknown",
        "skills": [],
        "domain_tags": [],
        "years_experience_min": None,
        "years_experience_max": None,
        "education_level": "unknown",
        "education_fields": [],
        "certifications": [],
        "locations": [],
        "workplace_type": "unknown",
        "employment_type": "unknown",
        "contract_duration": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_period": "unknown",
        "visa_sponsorship": "unknown",
        "work_authorization_required": None,
        "citizenship_requirement": None,
        "security_clearance_required": None,
        "security_clearance_level": None,
        "offices": [],
        "confidence": 0.9,
    }
    payload.update(overrides)
    return payload


def test_v3_schema_requires_every_dimension():
    properties = set(
        JOB_ENRICHMENT_V3_JSON_SCHEMA[
            "properties"
        ]
    )

    required = set(
        JOB_ENRICHMENT_V3_JSON_SCHEMA.get(
            "required",
            [],
        )
    )

    assert required == properties


def test_v3_rejects_confidence_only_output():
    with pytest.raises(ValidationError):
        JobEnrichmentV3.model_validate(
            {"confidence": 0.9}
        )


def test_v3_location_objects_require_explicit_nullable_keys():
    location_schema = JOB_ENRICHMENT_V3_JSON_SCHEMA["$defs"][
        "EnrichedLocationV3"
    ]

    assert set(location_schema["required"]) == set(
        location_schema["properties"]
    )


@pytest.mark.parametrize("provider", ["greenhouse", "lever"])
def test_trusted_ats_facts_survive_when_absent_from_ai_output(provider):
    result = JobEnrichmentV3.model_validate(complete_v3_payload())
    context = {
        "locations": ["Paris, France"],
        "offices": ["Paris HQ"],
        "employment_type": "FullTime",
        "workplace_type": "Hybrid",
        "salary": {
            "min": 90_000,
            "max": 110_000,
            "currency": "eur",
            "interval": "yearly",
        },
    }

    _merge_trusted_ats_facts(
        result,
        {"provider": provider, "raw_payload": {}},
        context,
    )

    assert result.locations[0].city == "Paris, France"
    assert result.offices == ["Paris HQ"]
    assert result.employment_type == "full_time"
    assert result.workplace_type == "hybrid"
    assert result.salary_min == 90_000
    assert result.salary_max == 110_000
    assert result.salary_currency == "EUR"
    assert result.salary_period == "year"


def test_v3_compact_skills():
    result = JobEnrichmentV3.model_validate(
        complete_v3_payload(
            standardized_title="Senior Backend Engineer",
            skills=[
                {"name": "Python", "requirement": "required"},
                {"name": "AWS", "requirement": "preferred"},
                {"name": "Docker", "requirement": "mentioned"},
            ],
        )
    )

    assert [entry.model_dump() for entry in result.skills] == [
        {"name": "Python", "requirement": "required"},
        {"name": "AWS", "requirement": "preferred"},
        {"name": "Docker", "requirement": "mentioned"},
    ]


def test_v3_compact_certifications():
    result = JobEnrichmentV3.model_validate(
        complete_v3_payload(
            certifications=[
                {"name": "CPA", "requirement": "required"},
                {"name": "CFA", "requirement": "preferred"},
            ],
            confidence=0.85,
        )
    )

    assert [entry.model_dump() for entry in result.certifications] == [
        {"name": "CPA", "requirement": "required"},
        {"name": "CFA", "requirement": "preferred"},
    ]


def test_v3_deduplicates_skill_aliases_using_strongest_requirement():
    result = JobEnrichmentV3.model_validate(
        complete_v3_payload(
            skills=[
                {"name": "JS", "requirement": "mentioned"},
                {"name": "javascript", "requirement": "required"},
                {"name": " JAVASCRIPT ", "requirement": "preferred"},
            ],
            certifications=[
                {"name": "PMP", "requirement": "preferred"},
                {"name": "pmp", "requirement": "required"},
            ],
        )
    )

    assert [entry.model_dump() for entry in result.skills] == [
        {"name": "JavaScript", "requirement": "required"}
    ]
    assert len(result.certifications) == 1
    assert result.certifications[0].requirement == "required"


def test_v3_does_not_have_removed_fields():
    properties = (
        JOB_ENRICHMENT_V3_JSON_SCHEMA[
            "properties"
        ]
    )

    removed = {
        "role_track",
        "leadership_level",
        "people_management",

        "required_skills",
        "preferred_skills",
        "programming_languages",
        "frameworks",
        "databases",
        "cloud_platforms",
        "devops_tools",
        "data_tools",
        "ml_ai_tools",
        "analytics_tools",
        "product_tools",
        "crm_tools",
        "security_tools",
        "methodologies",
        "architecture_patterns",
        "platform_domains",
        "soft_skills",
        "responsibility_tags",

        "management_experience_required",
        "management_years_min",
        "industry_experience_required",

        "education_required",
        "education_preferred",
        "equivalent_experience_allowed",
        "required_certifications",
        "preferred_certifications",
        "professional_license_required",

        "schedule_type",
        "travel_required",
        "travel_percentage",
        "on_call_required",

        "export_control_restriction",

        "departments",
        "teams",
        "business_function",
        "product_area",

        "required_languages",
        "preferred_languages",

        "benefits",
    }

    assert not (
        removed
        & set(properties)
    )
