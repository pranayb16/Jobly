from urllib.parse import urlparse

import pytest
import requests
from rich import print_json

from crawlers.models import Job
from crawlers.normalize.greenhouse import normalize_greenhouse

GREENHOUSE_SOURCES = [
    "https://job-boards.greenhouse.io/westernunion",
    "https://job-boards.greenhouse.io/gymshark",
    "https://job-boards.greenhouse.io/goodnotes",
    "https://job-boards.greenhouse.io/forgehealth"
]

@pytest.mark.parametrize("career_url", GREENHOUSE_SOURCES)
def test_greenhouse_jobs(career_url):

    board_token = urlparse(career_url).path.strip("/").split("/")[0]

    api_url = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{board_token}/jobs?content=true"
    )

    response = requests.get(api_url, timeout=20)

    assert response.status_code == 200

    data = response.json()

    assert "jobs" in data
    assert len(data["jobs"]) > 0

    raw_job = data["jobs"][0]

    normalized_job = normalize_greenhouse(raw_job)

    assert isinstance(normalized_job, Job)

    assert normalized_job.provider == "greenhouse"
    assert normalized_job.external_job_id
    assert normalized_job.title
    assert normalized_job.job_url

    print(normalized_job.model_dump_json(indent=2))