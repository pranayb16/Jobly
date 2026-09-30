from urllib.parse import urlparse

from jobly.crawling.http_client import get_json
from jobly.crawling.normalize.lever import normalize_lever
from jobly.jobs.models import Job


def validate_lever_response(data: object) -> list[dict]:
    if not isinstance(data, list):
        raise ValueError("Lever response must be a list")
    return data


def fetch_lever_jobs(career_url: str) -> list[Job]:
    site_name = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://api.lever.co/v0/postings/"
        f"{site_name}?mode=json"
    )

    data = get_json(api_url)

    return [
        normalize_lever(raw_job, company=site_name)
        for raw_job in validate_lever_response(data)
    ]
