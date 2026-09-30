import json
from pathlib import Path

from jobly.crawling.normalize.ashby import normalize_ashby
from jobly.crawling.normalize.greenhouse import normalize_greenhouse
from jobly.crawling.normalize.lever import normalize_lever
from jobly.jobs.models import Job


FIXTURES = Path(__file__).parents[1] / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_greenhouse_normalization():
    job = normalize_greenhouse(load("greenhouse_jobs.json")["jobs"][0])
    assert isinstance(job, Job)
    assert job.provider == "greenhouse"
    assert job.external_job_id == "101"
    assert job.location == "Chicago, IL"
    assert job.description.text == "Build reliable services."


def test_ashby_normalization():
    job = normalize_ashby(load("ashby_jobs.json")["jobs"][0], company="example")
    assert job.provider == "ashby"
    assert job.external_job_id == "ashby-202"
    assert job.employment_type == "FullTime"
    assert job.apply_url.endswith("/apply")


def test_lever_normalization():
    job = normalize_lever(load("lever_jobs.json")[0], company="example")
    assert job.provider == "lever"
    assert job.external_job_id == "lever-303"
    assert job.posted_at is None
    assert job.description.text == "Help customers succeed."
