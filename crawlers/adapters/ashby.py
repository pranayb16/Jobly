# crawlers/adapters/ashby.py

import requests
from urllib.parse import urlparse

from crawlers.models import Job
from crawlers.normalize.ashby import normalize_ashby


def fetch_ashby_jobs(career_url: str) -> list[Job]:
    board_name = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://api.ashbyhq.com/posting-api/job-board/"
        f"{board_name}?includeCompensation=true"
    )

    response = requests.get(api_url, timeout=20)
    response.raise_for_status()

    data = response.json()

    return [
        normalize_ashby(raw_job, company=board_name)
        for raw_job in data.get("jobs", [])
    ]