from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg.types.json import Jsonb

from jobly.config import get_settings
from jobly.db.connection import get_connection


@dataclass(frozen=True)
class SnapshotSummary:
    snapshot_date: date
    snapshots_created: int


def _strings(value: Any) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _location_label(location: Any) -> str | None:
    if not isinstance(location, dict):
        return None
    parts = [location.get("city"), location.get("region"), location.get("country")]
    clean = [str(part).strip() for part in parts if part]
    return ", ".join(clean) or None


def calculate_coverage(enriched_jobs: int, total_open_jobs: int) -> float:
    return enriched_jobs / total_open_jobs if total_open_jobs else 0.0


def calculate_ai_counts(enrichments: list[dict]) -> dict[str, dict[str, int]]:
    roles: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    seniority: Counter[str] = Counter()
    locations: Counter[str] = Counter()
    workplaces: Counter[str] = Counter()
    domains: Counter[str] = Counter()
    for data in enrichments:
        role = data.get("standardized_title") or data.get("job_family")
        if role:
            roles[str(role)] += 1
        for skill in set(_strings(data.get("required_skills")) + _strings(data.get("preferred_skills"))):
            skills[skill] += 1
        if data.get("seniority") and data["seniority"] != "unknown":
            seniority[str(data["seniority"])] += 1
        for location in data.get("locations", []):
            label = _location_label(location)
            if label:
                locations[label] += 1
        if data.get("workplace_type") and data["workplace_type"] != "unknown":
            workplaces[str(data["workplace_type"])] += 1
        for domain in _strings(data.get("domain_tags")):
            domains[domain] += 1
    return {
        "role_counts": dict(roles),
        "skill_counts": dict(skills),
        "seniority_counts": dict(seniority),
        "location_counts": dict(locations),
        "workplace_counts": dict(workplaces),
        "domain_counts": dict(domains),
    }


def build_snapshots(snapshot_date: date | None = None) -> SnapshotSummary:
    day = snapshot_date or date.today()
    schema_version = get_settings().ai_classification_version
    created = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM companies ORDER BY id")
            company_ids = [row[0] for row in cur.fetchall()]

        for company_id in company_ids:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM jobs WHERE company_id = %s AND active = TRUE),
                        COUNT(*) FILTER (WHERE e.event_type = 'created'),
                        COUNT(*) FILTER (WHERE e.event_type = 'removed'),
                        COUNT(*) FILTER (WHERE e.event_type = 'changed')
                    FROM job_events AS e
                    JOIN jobs AS j ON j.id = e.job_id
                    WHERE j.company_id = %s AND e.occurred_at::date = %s
                    """,
                    (company_id, company_id, day),
                )
                total_open, new_jobs, removed_jobs, changed_jobs = cur.fetchone()
                cur.execute(
                    """
                    SELECT e.data
                    FROM jobs AS j
                    JOIN job_enrichments AS e
                      ON e.job_id = j.id AND e.content_hash = j.content_hash
                    WHERE j.company_id = %s AND j.active = TRUE AND e.schema_version = %s
                    """,
                    (company_id, schema_version),
                )
                enrichment_data = [row[0] for row in cur.fetchall()]
                enriched_jobs = len(enrichment_data)
                coverage = calculate_coverage(enriched_jobs, total_open)
                counts = calculate_ai_counts(enrichment_data)
                cur.execute(
                    """
                    INSERT INTO company_daily_snapshots (
                        company_id, snapshot_date, total_open_jobs, new_jobs, removed_jobs,
                        changed_jobs, enriched_jobs, enrichment_coverage, role_counts,
                        skill_counts, seniority_counts, location_counts, workplace_counts,
                        domain_counts
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, snapshot_date) DO UPDATE SET
                        total_open_jobs = EXCLUDED.total_open_jobs,
                        new_jobs = EXCLUDED.new_jobs, removed_jobs = EXCLUDED.removed_jobs,
                        changed_jobs = EXCLUDED.changed_jobs,
                        enriched_jobs = EXCLUDED.enriched_jobs,
                        enrichment_coverage = EXCLUDED.enrichment_coverage,
                        role_counts = EXCLUDED.role_counts, skill_counts = EXCLUDED.skill_counts,
                        seniority_counts = EXCLUDED.seniority_counts,
                        location_counts = EXCLUDED.location_counts,
                        workplace_counts = EXCLUDED.workplace_counts,
                        domain_counts = EXCLUDED.domain_counts
                    """,
                    (
                        company_id, day, total_open, new_jobs, removed_jobs, changed_jobs,
                        enriched_jobs, coverage, Jsonb(counts["role_counts"]),
                        Jsonb(counts["skill_counts"]), Jsonb(counts["seniority_counts"]),
                        Jsonb(counts["location_counts"]), Jsonb(counts["workplace_counts"]),
                        Jsonb(counts["domain_counts"]),
                    ),
                )
            conn.commit()
            created += 1
    return SnapshotSummary(day, created)
