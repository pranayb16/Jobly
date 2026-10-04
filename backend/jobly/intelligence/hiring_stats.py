from __future__ import annotations

from dataclasses import dataclass

from jobly.db.connection import (
    get_connection,
)


@dataclass(
    frozen=True
)
class HiringStatsSummary:

    companies_refreshed: int

    publishable_companies: int

    unpublishable_companies: int


def refresh_hiring_stats(
    company_id: int | None = None,
) -> HiringStatsSummary:

    if (
        company_id is not None
        and company_id < 1
    ):
        raise ValueError(
            "company_id must be at least 1"
        )


    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    refresh_company_hiring_stats(
                        %s
                    )
                """,
                (
                    company_id,
                ),
            )

            row = cur.fetchone()

            companies_refreshed = int(
                row[0]
                if row
                else 0
            )


            if company_id is None:

                cur.execute(
                    """
                    SELECT

                        COUNT(*) FILTER (
                            WHERE
                                is_publishable = TRUE
                        ),

                        COUNT(*) FILTER (
                            WHERE
                                is_publishable = FALSE
                        )

                    FROM company_hiring_stats
                    """
                )

            else:

                cur.execute(
                    """
                    SELECT

                        COUNT(*) FILTER (
                            WHERE
                                is_publishable = TRUE
                        ),

                        COUNT(*) FILTER (
                            WHERE
                                is_publishable = FALSE
                        )

                    FROM company_hiring_stats

                    WHERE company_id = %s
                    """,
                    (
                        company_id,
                    ),
                )


            counts = (
                cur.fetchone()
                or (0, 0)
            )


        conn.commit()


    return HiringStatsSummary(

        companies_refreshed=(
            companies_refreshed
        ),

        publishable_companies=int(
            counts[0]
            or 0
        ),

        unpublishable_companies=int(
            counts[1]
            or 0
        ),
    )