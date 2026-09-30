from urllib.parse import urlparse

from jobly.crawling.http_client import get_json
from jobly.crawling.normalize.ashby import normalize_ashby
from jobly.jobs.models import Job


def validate_ashby_response(data: object) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("Ashby response must be an object")
    if "jobs" not in data:
        raise ValueError("Ashby response is missing the jobs field")
    jobs = data["jobs"]
    if not isinstance(jobs, list):
        raise ValueError("Ashby response jobs field must be a list")
    return jobs


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

    data = get_json(api_url)
    raw_jobs = validate_ashby_response(data)

    return [
        normalize_ashby(
            raw_job,
            company=board_name,
        )
        for raw_job
        in raw_jobs
    ]
