import threading

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


_local = threading.local()


def _create_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.75,
        status_forcelist=(
            429,
            500,
            502,
            503,
            504,
        ),
        allowed_methods=frozenset(
            ["GET"]
        ),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=20,
        pool_maxsize=20,
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )

    session.headers.update({
        "User-Agent": "Jobly/0.1",
        "Accept": "application/json",
    })

    return session


def get_session() -> requests.Session:
    if not hasattr(
        _local,
        "session",
    ):
        _local.session = _create_session()

    return _local.session


def get_json(
    url: str,
    timeout: int = 20,
):
    response = get_session().get(
        url,
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()
