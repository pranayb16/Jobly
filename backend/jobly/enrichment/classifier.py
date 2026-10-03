import json
from google import genai

from jobly.config import get_settings
from jobly.enrichment.prompt import SYSTEM_PROMPT
from jobly.enrichment.prompt_v2 import SYSTEM_PROMPT_V2
from jobly.enrichment.schemas import (
    JOB_CLASSIFICATION_JSON_SCHEMA,
    JobClassification,
)
from jobly.enrichment.schemas_v2 import JOB_ENRICHMENT_V2_JSON_SCHEMA, JobEnrichmentV2


def get_client() -> genai.Client:
    return genai.Client(api_key=get_settings().require_gemini_api_key())


def build_prompt(
    payload: dict,
    *,
    schema_version: str = "v1",
) -> str:

    job_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = SYSTEM_PROMPT_V2 if schema_version == "v2" else SYSTEM_PROMPT
    return f"""
{system_prompt}

Below is the job posting data that must be classified.

Use the structured ATS fields as factual context.

Do not invent skills, locations, experience requirements,
or related roles that are not supported by the posting.

JOB DATA:

{job_json}
""".strip()


def classify_job(
    payload: dict,
    *,
    schema_version: str | None = None,
) -> JobClassification | JobEnrichmentV2:

    schema_version = schema_version or get_settings().ai_classification_version

    client = get_client()

    prompt = build_prompt(
        payload,
        schema_version=schema_version,
    )

    interaction = (
        client.interactions.create(
            model=get_settings().ai_model,

            input=prompt,

            response_format={
                "type": "text",

                "mime_type": (
                    "application/json"
                ),

                "schema": (
                    JOB_ENRICHMENT_V2_JSON_SCHEMA
                    if schema_version == "v2"
                    else JOB_CLASSIFICATION_JSON_SCHEMA
                ),
            },
        )
    )

    content = interaction.output_text

    if not content:
        raise RuntimeError(
            "Gemini returned an empty response"
        )

    # Validate Gemini output again with
    # our own Pydantic validators.
    model_class = JobEnrichmentV2 if schema_version == "v2" else JobClassification
    classification = model_class.model_validate_json(content)

    return classification
