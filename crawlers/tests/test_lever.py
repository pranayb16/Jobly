# tests/test_lever.py

from urllib.parse import urlparse

import requests
from rich import print_json


CAREER_URL = "https://jobs.lever.co/jobgether"


def test_lever_jobs():
    parsed = urlparse(CAREER_URL)

    site_name = parsed.path.strip("/").split("/")[0]

    assert site_name

    api_url = (
        f"https://api.lever.co/v0/postings/"
        f"{site_name}?mode=json"
    )

    response = requests.get(api_url, timeout=20)

    print("\nCareer URL:", CAREER_URL)
    print("Site name:", site_name)
    print("API URL:", api_url)
    print("Status:", response.status_code)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    print("Jobs found:", len(data))

    print_json(data=data[0])

    # if data:
    #     job = data[0]

    #     print("ID:", job.get("id"))
    #     print("Title:", job.get("text"))
    #     print("Categories:", job.get("categories"))
    #     print("Hosted URL:", job.get("hostedUrl"))
    #     print("Apply URL:", job.get("applyUrl"))