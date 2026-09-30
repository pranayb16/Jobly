import pandas as pd
from pathlib import Path

from jobly.crawling.runner import crawl_source


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = REPO_ROOT / "data" / "cleaned" / "supported_sources.csv"
VALID_FILE = REPO_ROOT / "data" / "cleaned" / "valid_sources.csv"
FAILED_FILE = REPO_ROOT / "data" / "cleaned" / "failed_sources.csv"


def main():
    df = pd.read_csv(INPUT_FILE)

    valid_rows = []
    failed_rows = []

    print(f"Loaded {len(df)} sources")

    for index, row in df.iterrows():
        provider = row["ats_platform"]
        career_url = row["canonical_url"]

        print(
            f"[{index + 1}/{len(df)}] "
            f"{provider} | {career_url}"
        )

        try:
            jobs = crawl_source(
                provider,
                career_url,
            )

            valid_rows.append({
                "ats_platform": provider,
                "canonical_url": career_url,
                "jobs_found": len(jobs),
                "status": (
                    "valid"
                    if len(jobs) > 0
                    else "empty_valid"
                ),
            })

            print(f"  OK | jobs={len(jobs)}")

        except Exception as exc:
            failed_rows.append({
                "ats_platform": provider,
                "canonical_url": career_url,
                "status": "failed",
                "error": str(exc),
            })

            print(f"  FAILED | {exc}")

    pd.DataFrame(valid_rows).to_csv(
        VALID_FILE,
        index=False,
    )

    pd.DataFrame(failed_rows).to_csv(
        FAILED_FILE,
        index=False,
    )

    print()
    print("Validation complete")
    print("Valid:", len(valid_rows))
    print("Failed:", len(failed_rows))


if __name__ == "__main__":
    main()
