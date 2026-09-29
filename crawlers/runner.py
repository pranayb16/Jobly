import csv
import logging

from crawlers.adapters.ashby import fetch_ashby_jobs
from crawlers.adapters.greenhouse import fetch_greenhouse_jobs
from crawlers.adapters.lever import fetch_lever_jobs


logging.basicConfig(
    filename="crawler.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def crawl_source(provider: str, career_url: str):
    provider = provider.strip().lower()

    if provider == "greenhouse":
        return fetch_greenhouse_jobs(career_url)

    if provider == "ashby":
        return fetch_ashby_jobs(career_url)

    if provider == "lever":
        return fetch_lever_jobs(career_url)

    raise ValueError(
        f"Unsupported provider: {provider}"
    )


def load_sources(path: str) -> list[dict]:
    with open(
        path,
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def run():
    sources = load_sources(
        "crawlers/data/sources.csv"
    )

    all_jobs = []

    print(f"Loaded {len(sources)} sources")

    for index, source in enumerate(
        sources,
        start=1,
    ):
        provider = source["ats_platform"]
        career_url = source["canonical_url"]

        logging.info(
            "[%s/%s] START | %s | %s",
            index,
            len(sources),
            provider,
            career_url,
        )

        try:
            jobs = crawl_source(
                provider,
                career_url,
            )

            all_jobs.extend(jobs)

            logging.info(
                "[%s/%s] SUCCESS | %s | jobs=%s",
                index,
                len(sources),
                provider,
                len(jobs),
            )

        except Exception:
            logging.exception(
                "[%s/%s] FAILED | %s | %s",
                index,
                len(sources),
                provider,
                career_url,
            )

    print()
    print("Finished")
    print("Total jobs:", len(all_jobs))

    return all_jobs


if __name__ == "__main__":
    run()