 # crawlers/adapters/lever.py

import requests
from urllib.parse import urlparse

from crawlers.models import Job
from crawlers.normalize.lever import normalize_lever


def fetch_lever_jobs(career_url: str) -> list[Job]:
    site_name = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://api.lever.co/v0/postings/"
        f"{site_name}?mode=json"
    )

    response = requests.get(api_url, timeout=20)
    response.raise_for_status()

    data = response.json()

    return [
        normalize_lever(raw_job, company=site_name)
        for raw_job in data
    ]