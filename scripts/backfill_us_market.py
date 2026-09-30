from psycopg.rows import dict_row

from jobly.db.connection import (
    get_connection,
)

from jobly.market.us_scope import (
    classify_us_job,
)


BATCH_SIZE = 500


def main():

    total = 0
    us_count = 0
    excluded_count = 0

    last_id = 0


    with get_connection() as conn:

        while True:

            with conn.cursor(
                row_factory=dict_row
            ) as cur:

                cur.execute(
                    """
                    SELECT
                        id,

                        provider,
                        location,

                        raw_payload,

                        classification_status

                    FROM jobs

                    WHERE id > %s

                    ORDER BY id

                    LIMIT %s
                    """,
                    (
                        last_id,
                        BATCH_SIZE,
                    ),
                )


                rows = (
                    cur.fetchall()
                )


            if not rows:
                break


            with conn.cursor() as cur:

                for row in rows:

                    decision = (
                        classify_us_job(
                            provider=(
                                row[
                                    "provider"
                                ]
                            ),

                            location=(
                                row[
                                    "location"
                                ]
                            ),

                            raw=(
                                row[
                                    "raw_payload"
                                ]
                            ),
                        )
                    )


                    if (
                        not decision.eligible

                        and row[
                            "classification_status"
                        ] == "pending"
                    ):

                        next_status = (
                            "skipped_non_us"
                        )

                    else:

                        next_status = (
                            row[
                                "classification_status"
                            ]
                        )


                    cur.execute(
                        """
                        UPDATE jobs

                        SET
                            is_us_job = %s,

                            us_location_reason =
                                %s,

                            classification_status =
                                %s

                        WHERE id = %s
                        """,
                        (
                            decision.eligible,

                            decision.reason,

                            next_status,

                            row["id"],
                        ),
                    )


                    total += 1


                    if decision.eligible:
                        us_count += 1

                    else:
                        excluded_count += 1


                    last_id = (
                        row["id"]
                    )


            conn.commit()


            print(
                (
                    f"Processed={total} | "
                    f"US={us_count} | "
                    f"excluded={excluded_count}"
                )
            )


    print()

    print(
        "U.S. backfill complete"
    )

    print(
        "Total:",
        total,
    )

    print(
        "U.S.:",
        us_count,
    )

    print(
        "Excluded:",
        excluded_count,
    )


if __name__ == "__main__":
    main()
