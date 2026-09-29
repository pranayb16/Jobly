import pandas as pd
from urllib.parse import urlparse

from crawlers.db import get_connection


INPUT_FILE = (
    "crawlers/data/cleaned/valid_sources.csv"
)


def extract_board_id(url: str) -> str | None:
    parsed = urlparse(url)

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if not parts:
        return None

    return parts[0]


def main():
    df = pd.read_csv(INPUT_FILE)

    print(f"Loading {len(df)} verified sources")

    with get_connection() as conn:

        with conn.cursor() as cur:

            for _, row in df.iterrows():

                provider = (
                    row["ats_platform"]
                    .strip()
                    .lower()
                )

                url = row["canonical_url"]

                board_id = extract_board_id(url)

                cur.execute(
                    """
                    INSERT INTO sources (
                        provider,
                        canonical_url,
                        board_id
                    )
                    VALUES (%s, %s, %s)

                    ON CONFLICT (
                        provider,
                        canonical_url
                    )
                    DO NOTHING
                    """,
                    (
                        provider,
                        url,
                        board_id,
                    ),
                )

        conn.commit()

    print("Sources imported")


if __name__ == "__main__":
    main()