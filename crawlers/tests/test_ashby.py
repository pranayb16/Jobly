from urllib.parse import urlparse

import requests
from rich import print_json

CAREER_URL = 'https://jobs.ashbyhq.com/plaid'

def test_ashby_jobs():
    parsed = urlparse(CAREER_URL)

    board_token = parsed.path.strip("/").split("/")[0]

    assert board_token

    api_url = (
        f"https://api.ashbyhq.com/posting-api/job-board/"
        f"{board_token}"
    )

    response = requests.get(api_url, timeout=20)

    print("\nCareer URL:", CAREER_URL)
    print("Board token:", board_token)
    print("API URL:", api_url)
    print("Status:", response.status_code)

    assert response.status_code == 200

    data = response.json()

    assert "jobs" in data
    assert isinstance(data["jobs"], list)

    print("Jobs found:", len(data["jobs"]))

    print_json(data=data['jobs'][0])

    # if data["jobs"]:
    #     job = data["jobs"][0]

    #     print("Title:", job.get("title"))
    #     print("Location:", job.get("location"))
    #     print("Published:", job.get("publishedAt"))
    #     print("Job URL:", job.get("jobUrl"))
    #     print("Apply URL:", job.get("applyUrl"))