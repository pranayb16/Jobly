from pathlib import Path

import pandas as pd


RAW_FILE = Path("crawlers/data/raw/ats_career_page_urls.csv")
CLEANED_DIR = Path("crawlers/data/cleaned")


def main():
    CLEANED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(RAW_FILE)

    print("Original rows:", len(df))

    supported = df[
        df["ats_platform"].isin(
            [
                "Greenhouse",
                "Ashby",
                "Lever",
            ]
        )
    ].copy()

    print("Supported rows:", len(supported))

    supported.to_csv(
        CLEANED_DIR / "supported_sources.csv",
        index=False,
    )

    print(
        "Saved:",
        CLEANED_DIR / "supported_sources.csv",
    )


if __name__ == "__main__":
    main()