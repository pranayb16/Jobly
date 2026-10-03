from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

from jobly.config import get_settings
from jobly.enrichment.prompt_v2 import SYSTEM_PROMPT_V2
from jobly.enrichment.prompt_v3 import SYSTEM_PROMPT_V3
from jobly.enrichment.schemas_v2 import (
    JOB_ENRICHMENT_V2_JSON_SCHEMA,
    JobEnrichmentV2,
)
from jobly.enrichment.schemas_v3 import (
    JOB_ENRICHMENT_V3_JSON_SCHEMA,
    JobEnrichmentV3,
)


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# OpenRouter free models are limited to 20 requests/minute.
# 3.1 seconds keeps us slightly below that limit.
FREE_REQUEST_INTERVAL_SECONDS = 3.1


_last_free_request_at: float | None = None
_free_unavailable_for_run = False


@dataclass(frozen=True)
class GeminiUsage:
    """
    Kept under the old name temporarily so worker.py does not
    need a large refactor.

    These values now come from OpenRouter.
    """

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
        f"JOB DATA:\n"
        f"{job_json}"
    )


def _wait_for_free_request_slot() -> None:
    global _last_free_request_at

    now = time.monotonic()

    if _last_free_request_at is not None:

        elapsed = (
            now
            - _last_free_request_at
        )

        remaining = (
            FREE_REQUEST_INTERVAL_SECONDS
            - elapsed
        )

        if remaining > 0:
            time.sleep(remaining)

    _last_free_request_at = (
        time.monotonic()
    )


def _request_openrouter(
    *,
    model: str,
    prompt: str,
    response_schema: dict,
) -> requests.Response:

    settings = get_settings()

    return requests.post(
        OPENROUTER_URL,

        headers={
            "Authorization": (
                "Bearer "
                + settings.require_openrouter_api_key()
            ),

            "Content-Type":
                "application/json",

            "HTTP-Referer":
                "https://jobly.dev",

            "X-Title":
                "Jobly",
        },

        json={
            "model": model,

            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            "response_format": {
                "type": "json_schema",

                "json_schema": {
                    "name":
                        "job_enrichment",

                    "strict":
                        True,

                    "schema":
                        response_schema,
                },
            },

            "provider": {
                "require_parameters": True,
            },

            "usage": {
                "include": True,
            },

            "temperature": 0,
        },

        timeout=120,
    )


def _usage_from_response(
    data: dict,
) -> GeminiUsage:

    usage = (
        data.get("usage")
        or {}
    )

    prompt_details = (
        usage.get(
            "prompt_tokens_details"
        )
        or {}
    )

    completion_details = (
        usage.get(
            "completion_tokens_details"
        )
        or {}
    )

    return GeminiUsage(
        interaction_id=data.get("id"),

        input_tokens=int(
            usage.get(
                "prompt_tokens",
                0,
            )
            or 0
        ),

        output_tokens=int(
            usage.get(
                "completion_tokens",
                0,
            )
            or 0
        ),

        thought_tokens=int(
            completion_details.get(
                "reasoning_tokens",
                0,
            )
            or 0
        ),

        cached_tokens=int(
            prompt_details.get(
                "cached_tokens",
                0,
            )
            or 0
        ),

        total_tokens=int(
            usage.get(
                "total_tokens",
                0,
            )
            or 0
        ),
    )


def _extract_error(
    response: requests.Response,
) -> str:

    try:
        data = response.json()

        error = data.get("error")

        if isinstance(error, dict):
            return str(
                error.get("message")
                or error
            )

        return str(
            error
            or data
        )

    except Exception:
        return response.text[:2000]


def classify_job(
    payload: dict,
    *,
    schema_version: str | None = None,
) -> ClassificationResult:

    global _free_unavailable_for_run

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

    prompt = build_prompt(
        payload,
        schema_version=requested_version,
    )

    response = None

    # --------------------------------------------------------
    # FREE ROUTE FIRST
    # --------------------------------------------------------

    if not _free_unavailable_for_run:

        _wait_for_free_request_slot()

        response = _request_openrouter(
            model=(
                settings
                .openrouter_free_model
            ),
            prompt=prompt,
            response_schema=response_schema,
        )

        if response.status_code == 429:

            # Free quota exhausted or free route rate-limited.
            # Switch to paid for the remainder of this run.
            _free_unavailable_for_run = True

            response = None

        elif response.status_code >= 500:

            # Free provider unavailable.
            # Fall back to paid for this request.
            response = None

        elif not response.ok:

            raise RuntimeError(
                "OpenRouter free request failed: "
                + _extract_error(response)
            )

    # --------------------------------------------------------
    # PAID FALLBACK
    # --------------------------------------------------------

    if response is None:

        response = _request_openrouter(
            model=(
                settings
                .openrouter_paid_model
            ),
            prompt=prompt,
            response_schema=response_schema,
        )

        if not response.ok:

            raise RuntimeError(
                "OpenRouter paid request failed: "
                + _extract_error(response)
            )

    data = response.json()

    choices = (
        data.get("choices")
        or []
    )

    if not choices:

        raise RuntimeError(
            "OpenRouter returned no choices"
        )

    content = (
        choices[0]
        .get("message", {})
        .get("content")
    )

    if not content:

        raise RuntimeError(
            "OpenRouter returned "
            "an empty response"
        )

    classification = (
        model_class.model_validate_json(
            content
        )
    )

    usage = _usage_from_response(
        data
    )

    return ClassificationResult(
        classification=classification,
        usage=usage,
    )