from __future__ import annotations

from jobly.companies.service import collision_safe_slug, company_slug, normalize_company_name


def ensure_company(cur, name: str | None, website_domain: str | None = None) -> int | None:
    if not name or not name.strip():
        return None

    display_name = " ".join(name.split())
    normalized_name = normalize_company_name(display_name)
    cur.execute(
        "SELECT id FROM companies WHERE normalized_name = %s",
        (normalized_name,),
    )
    existing = cur.fetchone()
    if existing is not None:
        company_id = existing[0] if not isinstance(existing, dict) else existing["id"]
        if website_domain:
            cur.execute(
                """
                UPDATE companies
                SET website_domain = COALESCE(website_domain, %s), updated_at = NOW()
                WHERE id = %s
                """,
                (website_domain, company_id),
            )
        return company_id

    slug = company_slug(display_name)
    cur.execute("SELECT normalized_name FROM companies WHERE slug = %s", (slug,))
    collision = cur.fetchone()
    if collision is not None:
        slug = collision_safe_slug(display_name, normalized_name)

    cur.execute(
        """
        INSERT INTO companies (name, normalized_name, slug, website_domain)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (normalized_name) DO UPDATE
        SET website_domain = COALESCE(companies.website_domain, EXCLUDED.website_domain),
            updated_at = NOW()
        RETURNING id
        """,
        (display_name, normalized_name, slug, website_domain),
    )
    row = cur.fetchone()
    return row[0] if not isinstance(row, dict) else row["id"]


def link_source_company(cur, source_id: int, company_id: int | None) -> None:
    if company_id is None:
        return
    cur.execute(
        "UPDATE sources SET company_id = COALESCE(company_id, %s) WHERE id = %s",
        (company_id, source_id),
    )
