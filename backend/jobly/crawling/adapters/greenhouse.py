from urllib.parse import urlparse

from jobly.crawling.http_client import get_json
from jobly.crawling.normalize.greenhouse import normalize_greenhouse
from jobly.jobs.models import Job


def validate_greenhouse_response(data: object) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError("Greenhouse response must be an object")
    if "jobs" not in data:
        raise ValueError("Greenhouse response is missing the jobs field")
    jobs = data["jobs"]
    if not isinstance(jobs, list):
        raise ValueError("Greenhouse response jobs field must be a list")
    return jobs


def fetch_greenhouse_jobs(career_url: str) -> list[Job]:
    board_token = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{board_token}/jobs?content=true"
    )

    data = get_json(api_url)

    return [normalize_greenhouse(raw_job) for raw_job in validate_greenhouse_response(data)]
