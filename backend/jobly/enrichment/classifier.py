import json
from google import genai

from jobly.config import get_settings
from jobly.enrichment.prompt import SYSTEM_PROMPT
from jobly.enrichment.schemas import (
    JOB_CLASSIFICATION_JSON_SCHEMA,
    JobClassification,
)


def get_client() -> genai.Client:
    return genai.Client(api_key=get_settings().require_gemini_api_key())


def build_prompt(
    payload: dict,
) -> str:

    job_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
{SYSTEM_PROMPT}

Below is the job posting data that must be classified.

Use the structured ATS fields as factual context.

Do not invent skills, locations, experience requirements,
or related roles that are not supported by the posting.

JOB DATA:

{job_json}
""".strip()


def classify_job(
    payload: dict,
) -> JobClassification:

    client = get_client()

    prompt = build_prompt(
        payload
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

                "schema": JOB_CLASSIFICATION_JSON_SCHEMA,
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
    classification = (
        JobClassification
        .model_validate_json(content)
    )

    return classification
