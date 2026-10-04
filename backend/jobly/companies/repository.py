from __future__ import annotations

from jobly.companies.service import (
    collision_safe_slug,
    company_slug,
    normalize_company_name,
)


def ensure_company(
    cur,
    name: str | None,
    website_domain: str | None = None,
) -> int | None:

    if not name or not name.strip():
        return None


    display_name = " ".join(
        name.split()
    )

    normalized_name = (
        normalize_company_name(
            display_name
        )
    )


    cur.execute(
        """
        SELECT
            id,
            tracking_started_at,
            website_domain

        FROM companies

        WHERE normalized_name = %s
        """,
        (
            normalized_name,
        ),
    )


    existing = cur.fetchone()


    if existing is not None:

        if isinstance(
            existing,
            dict,
        ):

            company_id = (
                existing["id"]
            )

            tracking_started_at = (
                existing.get(
                    "tracking_started_at"
                )
            )

            current_website_domain = (
                existing.get(
                    "website_domain"
                )
            )

        else:

            (
                company_id,
                tracking_started_at,
                current_website_domain,
            ) = existing


        needs_tracking_start = (
            tracking_started_at
            is None
        )

        needs_domain = (
            website_domain is not None
            and current_website_domain
            is None
        )


        if (
            needs_tracking_start
            or needs_domain
        ):

            cur.execute(
                """
                UPDATE companies

                SET
                    website_domain =
                        COALESCE(
                            website_domain,
                            %s
                        ),

                    tracking_started_at =
                        COALESCE(
                            tracking_started_at,
                            NOW()
                        ),

                    updated_at =
                        NOW()

                WHERE id = %s
                """,
                (
                    website_domain,
                    company_id,
                ),
            )


        return company_id


    slug = company_slug(
        display_name
    )


    cur.execute(
        """
        SELECT normalized_name

        FROM companies

        WHERE slug = %s
        """,
        (
            slug,
        ),
    )


    collision = cur.fetchone()


    if collision is not None:

        slug = collision_safe_slug(
            display_name,
            normalized_name,
        )


    cur.execute(
        """
        INSERT INTO companies (
            name,
            normalized_name,
            slug,
            website_domain,
            tracking_started_at
        )

        VALUES (
            %s,
            %s,
            %s,
            %s,
            NOW()
        )

        ON CONFLICT (
            normalized_name
        )

        DO UPDATE SET

            website_domain =
                COALESCE(
                    companies.website_domain,
                    EXCLUDED.website_domain
                ),

            tracking_started_at =
                COALESCE(
                    companies.tracking_started_at,
                    NOW()
                ),

            updated_at =
                NOW()

        RETURNING id
        """,
        (
            display_name,
            normalized_name,
            slug,
            website_domain,
        ),
    )


    row = cur.fetchone()


    return (
        row[0]
        if not isinstance(
            row,
            dict,
        )
        else row["id"]
    )


def link_source_company(
    cur,
    source_id: int,
    company_id: int | None,
) -> None:

    if company_id is None:
        return


    cur.execute(
        """
        UPDATE sources

        SET company_id =
            COALESCE(
                company_id,
                %s
            )

        WHERE id = %s
        """,
        (
            company_id,
            source_id,
        ),
    )