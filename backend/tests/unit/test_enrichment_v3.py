from jobly.enrichment.schemas_v3 import (
    JOB_ENRICHMENT_V3_JSON_SCHEMA,
    JobEnrichmentV3,
)


def test_v3_schema_is_sparse():
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

    # v3 must NOT force every field into
    # every Gemini response.
    assert required != properties

    # Confidence may remain required.
    assert required <= {
        "confidence"
    }


def test_v3_compact_skills():
    result = JobEnrichmentV3(
        standardized_title=(
            "Senior Backend Engineer"
        ),

        skills={
            "Python": "required",
            "AWS": "preferred",
            "Docker": "mentioned",
        },

        confidence=0.9,
    )

    assert result.skills == {
        "Python": "required",
        "AWS": "preferred",
        "Docker": "mentioned",
    }


def test_v3_compact_certifications():
    result = JobEnrichmentV3(
        certifications={
            "CPA": "required",
            "CFA": "preferred",
        },

        confidence=0.85,
    )

    assert result.certifications == {
        "CPA": "required",
        "CFA": "preferred",
    }


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