 # crawlers/adapters/lever.py

from crawlers.http_client import get_json
from urllib.parse import urlparse

from crawlers.models import Job
from crawlers.normalize.lever import normalize_lever


def fetch_lever_jobs(career_url: str) -> list[Job]:
    site_name = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://api.lever.co/v0/postings/"
        f"{site_name}?mode=json"
    )

    data = get_json(api_url)

    return [
        normalize_lever(raw_job, company=site_name)
        for raw_job in data
    ]