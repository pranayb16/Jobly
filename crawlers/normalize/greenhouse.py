from crawlers.models import Job,JobDescription

from bs4 import BeautifulSoup
import html

def greenhouse_description(content: str | None) -> JobDescription:
    if not content:
        return JobDescription()

    decoded_html = html.unescape(content)

    soup = BeautifulSoup(decoded_html, "html.parser")
    text = soup.get_text("\n", strip=True)

    return JobDescription(
        html=decoded_html,
        text=text,
    )


def normalize_greenhouse(raw: dict) -> Job:
    return Job(
        external_job_id=str(raw["id"]),
        provider="greenhouse",

        company=raw.get("company_name"),
        title=raw["title"],

        location=(raw.get("location") or {}).get("name"),

        posted_at=raw.get("first_published"),
        posted_at_source="greenhouse.first_published",

        description=greenhouse_description(
            raw.get("content")
        ),

        job_url=raw.get("absolute_url"),

        raw=raw,
    )