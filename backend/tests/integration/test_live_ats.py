import pytest

from jobly.crawling.adapters.ashby import fetch_ashby_jobs
from jobly.crawling.adapters.greenhouse import fetch_greenhouse_jobs
from jobly.crawling.adapters.lever import fetch_lever_jobs


pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("fetcher", "url"),
    [
        (fetch_greenhouse_jobs, "https://job-boards.greenhouse.io/gymshark"),
        (fetch_ashby_jobs, "https://jobs.ashbyhq.com/plaid"),
        (fetch_lever_jobs, "https://jobs.lever.co/jobgether"),
    ],
)
def test_live_provider(fetcher, url):
    jobs = fetcher(url)
    assert isinstance(jobs, list)
