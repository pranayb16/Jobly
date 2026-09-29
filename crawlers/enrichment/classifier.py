import json
import os

from google import genai

from crawlers.enrichment.prompt import SYSTEM_PROMPT
from crawlers.enrichment.schemas import (
    JOB_CLASSIFICATION_JSON_SCHEMA,
    JobClassification,
)


MODEL = os.getenv(
    "AI_MODEL",
    "gemini-3.5-flash-lite",
)


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured"
        )

    return genai.Client(
        api_key=api_key,
    )


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
            model=MODEL,

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