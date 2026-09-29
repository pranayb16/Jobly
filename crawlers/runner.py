import csv

from crawlers.adapters.greenhouse import fetch_greenhouse_jobs
from crawlers.adapters.ashby import fetch_ashby_jobs
from crawlers.adapters.lever import fetch_lever_jobs

import logging

logging.basicConfig(
    filename="crawler.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def crawl_source(provider: str, career_url: str):
    provider = provider.lower()

    if provider == "greenhouse":
        return fetch_greenhouse_jobs(career_url)

    if provider == "ashby":
        return fetch_ashby_jobs(career_url)

    if provider == "lever":
        return fetch_lever_jobs(career_url)

    raise ValueError(f"Unsupported provider: {provider}")


def load_sources(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def run():
    sources = load_sources(
        "crawlers/data/sources.csv"
    )

    all_jobs = []

    print(f"Loaded {len(sources)} sources")

    for index, source in enumerate(sources, start=1):
        for source in sources:
            provider = source["ats_platform"]
            career_url = source["canonical_url"]

            logging.info(
                f"START | {provider} | {career_url}"
            )

            try:
                jobs = crawl_source(
                    provider,
                    career_url,
                )

                logging.info(
                    f"SUCCESS | {provider} | {career_url} | jobs={len(jobs)}"
                )

            except Exception as e:
                logging.error(
                    f"FAILED | {provider} | {career_url} | error={e}"
                )

    print()
    print("Finished")
    print("Total jobs:", len(all_jobs))

    return all_jobs


if __name__ == "__main__":
    run()