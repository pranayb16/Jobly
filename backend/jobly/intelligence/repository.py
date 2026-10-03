from __future__ import annotations

from datetime import date

from psycopg.rows import dict_row


def list_companies(conn, *, limit: int, offset: int) -> tuple[int, list[dict]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT COUNT(*) AS count FROM companies")
        total = cur.fetchone()["count"]
        cur.execute(
            """
            SELECT c.id, c.name, c.slug, c.website_domain,
                   s.snapshot_date, s.total_open_jobs, s.new_jobs, s.removed_jobs,
                   s.changed_jobs, s.enriched_jobs, s.enrichment_coverage,
                   s.role_counts, s.skill_counts, s.seniority_counts,
                   s.location_counts, s.workplace_counts, s.domain_counts
            FROM companies AS c
            LEFT JOIN LATERAL (
                SELECT * FROM company_daily_snapshots
                WHERE company_id = c.id ORDER BY snapshot_date DESC LIMIT 1
            ) AS s ON TRUE
            ORDER BY COALESCE(s.total_open_jobs, 0) DESC, c.name
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = list(cur.fetchall())
    return total, rows


def get_company(conn, slug: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT c.id, c.name, c.slug, c.website_domain,
                   s.snapshot_date, s.total_open_jobs, s.new_jobs, s.removed_jobs,
                   s.changed_jobs, s.enriched_jobs, s.enrichment_coverage,
                   s.role_counts, s.skill_counts, s.seniority_counts,
                   s.location_counts, s.workplace_counts, s.domain_counts
            FROM companies AS c
            LEFT JOIN LATERAL (
                SELECT * FROM company_daily_snapshots
                WHERE company_id = c.id ORDER BY snapshot_date DESC LIMIT 1
            ) AS s ON TRUE
            WHERE c.slug = %s
            """,
            (slug,),
        )
        return cur.fetchone()


def company_history(conn, company_id: int, days: int = 31) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT snapshot_date, total_open_jobs, new_jobs, removed_jobs, changed_jobs,
                   enriched_jobs, enrichment_coverage
            FROM company_daily_snapshots
            WHERE company_id = %s AND snapshot_date >= CURRENT_DATE - %s
            ORDER BY snapshot_date DESC
            """,
            (company_id, days),
        )
        return list(cur.fetchall())


def market_snapshot(conn, snapshot_date: date | None = None) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            WITH target AS (
                SELECT COALESCE(%s::date, MAX(snapshot_date)) AS day
                FROM company_daily_snapshots
            )
            SELECT target.day AS snapshot_date,
                   COUNT(s.company_id) AS companies_tracked,
                   COALESCE(SUM(s.total_open_jobs), 0) AS total_open_jobs,
                   COALESCE(SUM(s.new_jobs), 0) AS new_jobs,
                   COALESCE(SUM(s.removed_jobs), 0) AS removed_jobs,
                   COALESCE(SUM(s.changed_jobs), 0) AS changed_jobs,
                   COALESCE(SUM(s.enriched_jobs), 0) AS enriched_jobs
            FROM target
            LEFT JOIN company_daily_snapshots AS s ON s.snapshot_date = target.day
            GROUP BY target.day
            """,
            (snapshot_date,),
        )
        return cur.fetchone()


def aggregate_dimension(conn, dimension: str, limit: int = 50) -> list[dict]:
    allowed = {"role_counts", "skill_counts", "seniority_counts", "location_counts",
               "workplace_counts", "domain_counts"}
    if dimension not in allowed:
        raise ValueError("unsupported aggregate dimension")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            WITH latest AS (SELECT MAX(snapshot_date) AS day FROM company_daily_snapshots),
            expanded AS (
                SELECT entry.key AS name, SUM((entry.value)::text::integer) AS count
                FROM company_daily_snapshots AS s, latest,
                     LATERAL jsonb_each(s.{dimension}) AS entry
                WHERE s.snapshot_date = latest.day
                GROUP BY entry.key
            )
            SELECT name, count FROM expanded ORDER BY count DESC, name LIMIT %s
            """,
            (limit,),
        )
        return list(cur.fetchall())
