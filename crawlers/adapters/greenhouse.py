# crawlers/adapters/greenhouse.py

import requests
from urllib.parse import urlparse

from crawlers.models import Job
from crawlers.normalize.greenhouse import normalize_greenhouse


def fetch_greenhouse_jobs(career_url: str) -> list[Job]:
    board_token = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{board_token}/jobs?content=true"
    )

    response = requests.get(api_url, timeout=20)
    response.raise_for_status()

    data = response.json()

    return [
        normalize_greenhouse(raw_job)
        for raw_job in data.get("jobs", [])
    ]