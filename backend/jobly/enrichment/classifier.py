from __future__ import annotations

import logging
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

FREE_REQUEST_INTERVAL_SECONDS = 3.1

_last_free_request_at: float | None = None
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenRouterUsage:

    interaction_id: str | None = None
    model: str | None = None
    provider: str | None = None

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

    usage: OpenRouterUsage


class OpenRouterError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float = 0,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = status_code is None or status_code == 429 or status_code >= 500
        self.error_class = f"openrouter_http_{status_code}" if status_code else "openrouter_request"
        self.retry_after_seconds = retry_after_seconds


def build_messages(
    payload: dict,
    *,
    schema_version: str,
) -> list[dict]:

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

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": job_json,
        },
    ]


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
    messages: list[dict],
    response_schema: dict,
    providers: tuple[str, ...] | None = None,
) -> requests.Response:

    settings = get_settings()

    provider_config = {
        "require_parameters": True,
    }

    selected_providers = providers
    if selected_providers is None and model == settings.openrouter_paid_model:
        selected_providers = settings.openrouter_paid_providers

    if selected_providers:
        provider_config.update(
            {
                "order": list(selected_providers),
                "allow_fallbacks": False,
            }
        )

    body = {
        "model": model,
        "messages": messages,

        "response_format": {
            "type": "json_schema",

            "json_schema": {
                "name": "job_enrichment",
                "strict": True,
                "schema": response_schema,
            },
        },

        "provider": provider_config,

        "usage": {
            "include": True,
        },

        "temperature": 0,
        "max_tokens": settings.openrouter_max_output_tokens,
    }

    # GPT-OSS is used only as paid fallback.
    # Keep reasoning low for extraction work.
    if model == settings.openrouter_free_model:
        body["reasoning"] = {
            "enabled": False,
        }
    elif model == settings.openrouter_paid_model:
        body["reasoning"] = {
            # "enabled": False,
            "effort": "low",
        }

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

        json=body,

        timeout=120,
    )


def _usage_from_response(
    data: dict,
    *,
    fallback_model: str,
) -> OpenRouterUsage:

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

    def safe_int(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError, OverflowError):
            return 0

    return OpenRouterUsage(
        interaction_id=data.get("id"),

        model=(
            data.get("model")
            or fallback_model
        ),
        provider=data.get("provider"),

        input_tokens=safe_int(
            usage.get(
                "prompt_tokens",
                0,
            )
            or 0
        ),

        output_tokens=safe_int(
            usage.get(
                "completion_tokens",
                0,
            )
            or 0
        ),

        thought_tokens=safe_int(
            completion_details.get(
                "reasoning_tokens",
                0,
            )
            or 0
        ),

        cached_tokens=safe_int(
            prompt_details.get(
                "cached_tokens",
                0,
            )
            or 0
        ),

        total_tokens=safe_int(
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


def _free_error_allows_paid_fallback(
    response: requests.Response,
) -> bool:

    if response.status_code == 429:
        return True

    if response.status_code >= 500:
        return True

    message = (
        _extract_error(response)
        .lower()
    )

    fallback_phrases = (
        "unavailable for free",
        "paid version is available",
        "model is unavailable",
        "no endpoints found",
        "no endpoints available",
        "temporarily unavailable",
        "rate limit",
        "rate-limit",
        "rate limited",
    )

    return any(
        phrase in message
        for phrase in fallback_phrases
    )


def _retry_after_seconds(response: requests.Response) -> float:
    value = response.headers.get("Retry-After", "").strip()
    try:
        return max(0.0, min(float(value), 30.0))
    except ValueError:
        return 0.0


def _parse_response(
    response: requests.Response,
    *,
    model_class,
    fallback_model: str,
) -> ClassificationResult:

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
        data,
        fallback_model=fallback_model,
    )

    return ClassificationResult(
        classification=classification,
        usage=usage,
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

    messages = build_messages(
        payload,
        schema_version=requested_version,
    )

    # ========================================================
    # FREE FIRST — FOR EVERY JOB
    # ========================================================

    logger.info(
        "AI free attempt | model=%s",
        settings.openrouter_free_model,
    )

    _wait_for_free_request_slot()

    free_response: requests.Response | None = None

    try:
        free_response = _request_openrouter(
            model=settings.openrouter_free_model,
            messages=messages,
            response_schema=response_schema,
        )

    except requests.RequestException as exc:

        logger.warning(
            "AI free failed | model=%s | "
            "reason=request_error | error=%s | "
            "falling_back_to=%s",
            settings.openrouter_free_model,
            exc,
            settings.openrouter_paid_model,
        )

        free_response = None


    if free_response is not None:

        if free_response.ok:

            try:
                free_result = _parse_response(
                    free_response,
                    model_class=model_class,
                    fallback_model=(
                        settings.openrouter_free_model
                    ),
                )

                logger.info(
                    "AI free success | "
                    "requested_model=%s | "
                    "actual_model=%s",
                    settings.openrouter_free_model,
                    free_result.usage.model,
                )

                return free_result

            except Exception as exc:

                logger.warning(
                    "AI free rejected | model=%s | "
                    "reason=invalid_output | "
                    "error=%s | "
                    "falling_back_to=%s",
                    settings.openrouter_free_model,
                    exc,
                    settings.openrouter_paid_model,
                )

        else:

            error_message = (
                _extract_error(
                    free_response
                )
            )

            if _free_error_allows_paid_fallback(
                free_response
            ):

                retry_after = _retry_after_seconds(free_response)
                if retry_after:
                    time.sleep(retry_after)

                logger.warning(
                    "AI free failed | model=%s | "
                    "status=%s | error=%s | "
                    "falling_back_to=%s",
                    settings.openrouter_free_model,
                    free_response.status_code,
                    error_message,
                    settings.openrouter_paid_model,
                )

            else:

                raise OpenRouterError(
                    "OpenRouter free request failed: "
                    + error_message,
                    status_code=free_response.status_code,
                )

    # ========================================================
    # PAID FALLBACK — THIS JOB ONLY
    # ========================================================
    logger.info(
        "AI paid fallback | model=%s",
        settings.openrouter_paid_model,
    )
    try:
        paid_response = _request_openrouter(
            model=settings.openrouter_paid_model,
            messages=messages,
            response_schema=response_schema,
            providers=settings.openrouter_paid_providers,
        )

    except requests.RequestException as exc:

        raise OpenRouterError(
            "OpenRouter paid request failed: "
            f"{exc}"
        ) from exc

    if not paid_response.ok:

        raise OpenRouterError(
            "OpenRouter paid request failed: "
            + _extract_error(
                paid_response
            ),
            status_code=paid_response.status_code,
            retry_after_seconds=_retry_after_seconds(paid_response),
        )

    paid_result = _parse_response(
        paid_response,
        model_class=model_class,
        fallback_model=(
            settings.openrouter_paid_model
        ),
    )

    logger.info(
        "AI paid success | "
        "requested_model=%s | "
        "actual_model=%s",
        settings.openrouter_paid_model,
        paid_result.usage.model,
    )

    return paid_result
