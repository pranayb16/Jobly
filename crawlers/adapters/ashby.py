from urllib.parse import urlparse

import requests

from crawlers.models import Job
from crawlers.normalize.ashby import (
    normalize_ashby,
)


def fetch_ashby_jobs(
    career_url: str,
) -> list[Job]:

    parsed = urlparse(
        career_url
    )

    board_name = (
        parsed.path
        .strip("/")
        .split("/")[0]
    )

    if not board_name:
        raise ValueError(
            f"Invalid Ashby career URL: {career_url}"
        )

    api_url = (
        "https://api.ashbyhq.com/"
        "posting-api/job-board/"
        f"{board_name}"
        "?includeCompensation=true"
    )

    response = requests.get(
        api_url,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    raw_jobs = data.get(
        "jobs",
        [],
    )

    if not isinstance(
        raw_jobs,
        list,
    ):
        raise ValueError(
            "Ashby response did not contain a valid jobs list"
        )

    return [
        normalize_ashby(
            raw_job,
            company=board_name,
        )
        for raw_job
        in raw_jobs
    ]