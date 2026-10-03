from __future__ import annotations

import json
from dataclasses import dataclass

from google import genai

from jobly.config import get_settings
from jobly.enrichment.prompt_v2 import (
    SYSTEM_PROMPT_V2,
)
from jobly.enrichment.prompt_v3 import (
    SYSTEM_PROMPT_V3,
)
from jobly.enrichment.schemas_v2 import (
    JOB_ENRICHMENT_V2_JSON_SCHEMA,
    JobEnrichmentV2,
)
from jobly.enrichment.schemas_v3 import (
    JOB_ENRICHMENT_V3_JSON_SCHEMA,
    JobEnrichmentV3,
)


@dataclass(frozen=True)
class GeminiUsage:
    interaction_id: str | None = None

    input_tokens: int = 0
    output_tokens: int = 0
    thought_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ClassificationResult:
    classification: (
        JobEnrichmentV2
        | JobEnrichmentV3
    )

    usage: GeminiUsage


def get_client() -> genai.Client:
    settings = get_settings()

    return genai.Client(
        api_key=(
            settings.require_gemini_api_key()
        )
    )


def build_prompt(
    payload: dict,
    *,
    schema_version: str,
) -> str:
    job_json = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )

    if schema_version == "v3":
        system_prompt = SYSTEM_PROMPT_V3

    elif schema_version == "v2":
        system_prompt = SYSTEM_PROMPT_V2

    else:
        raise ValueError(
            "Unsupported enrichment schema: "
            f"{schema_version!r}"
        )

    return (
        f"{system_prompt}\n\n"
        f"JOB DATA:\n{job_json}"
    )


def _usage_from_interaction(
    interaction,
) -> GeminiUsage:
    usage = getattr(
        interaction,
        "usage",
        None,
    )

    interaction_id = getattr(
        interaction,
        "id",
        None,
    )

    if usage is None:
        return GeminiUsage(
            interaction_id=interaction_id
        )

    return GeminiUsage(
        interaction_id=interaction_id,

        input_tokens=int(
            getattr(
                usage,
                "total_input_tokens",
                0,
            )
            or 0
        ),

        output_tokens=int(
            getattr(
                usage,
                "total_output_tokens",
                0,
            )
            or 0
        ),

        thought_tokens=int(
            getattr(
                usage,
                "total_thought_tokens",
                0,
            )
            or 0
        ),

        cached_tokens=int(
            getattr(
                usage,
                "total_cached_tokens",
                0,
            )
            or 0
        ),

        total_tokens=int(
            getattr(
                usage,
                "total_tokens",
                0,
            )
            or 0
        ),
    )


def classify_job(
    payload: dict,
    *,
    schema_version: str | None = None,
) -> ClassificationResult:
    settings = get_settings()

    requested_version = (
        schema_version
        or settings.ai_classification_version
    )

    if requested_version == "v3":
        response_schema = (
            JOB_ENRICHMENT_V3_JSON_SCHEMA
        )

        model_class = JobEnrichmentV3

    elif requested_version == "v2":
        response_schema = (
            JOB_ENRICHMENT_V2_JSON_SCHEMA
        )

        model_class = JobEnrichmentV2

    else:
        raise ValueError(
            "Jobly enrichment supports "
            "'v2' and 'v3'. "
            f"Received: {requested_version!r}"
        )

    client = get_client()

    prompt = build_prompt(
        payload,
        schema_version=requested_version,
    )

    interaction = client.interactions.create(
        model=settings.ai_model,

        input=prompt,

        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema,
        },
    )

    content = interaction.output_text

    if not content:
        raise RuntimeError(
            "Gemini returned an empty response"
        )

    classification = (
        model_class.model_validate_json(
            content
        )
    )

    usage = _usage_from_interaction(
        interaction
    )

    return ClassificationResult(
        classification=classification,
        usage=usage,
    )