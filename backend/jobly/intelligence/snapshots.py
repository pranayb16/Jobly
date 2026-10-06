from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from jobly.config import get_settings
from jobly.db.connection import get_connection


@dataclass(frozen=True)
class SnapshotSummary:
    snapshot_date: date

    snapshots_created: int


def _strings(
    value: Any,
) -> list[str]:

    if not isinstance(
        value,
        list,
    ):
        return []

    return [
        item
        for item in value

        if (
            isinstance(
                item,
                str,
            )
            and item.strip()
        )
    ]


def _location_label(
    location: Any,
) -> str | None:

    if not isinstance(
        location,
        dict,
    ):
        return None

    parts = [
        location.get("city"),
        location.get("state"),
        location.get("country"),
    ]

    clean = [
        str(part).strip()
        for part in parts
        if part
    ]

    if not clean:
        return None

    return ", ".join(
        clean
    )


def calculate_coverage(
    enriched_jobs: int,
    total_open_jobs: int,
) -> float:

    if not total_open_jobs:
        return 0.0

    return (
        enriched_jobs
        /
        total_open_jobs
    )


def calculate_ai_counts(
    enrichments: list[dict],
) -> dict[str, dict[str, int]]:

    roles: Counter[str] = Counter()

    skills: Counter[str] = Counter()

    seniority: Counter[str] = Counter()

    locations: Counter[str] = Counter()

    workplaces: Counter[str] = Counter()

    domains: Counter[str] = Counter()

    for data in enrichments:

        # -----------------------------------------------------
        # Roles
        # -----------------------------------------------------

        role = data.get("standardized_title")

        if role:
            roles[
                str(role)
            ] += 1

        # -----------------------------------------------------
        # Skills
        # -----------------------------------------------------

        for skill in set(
            _strings(
                _strings(data.get("required_skills"))
                + _strings(data.get("preferred_skills"))
            )
        ):
            skills[
                skill
            ] += 1

        # -----------------------------------------------------
        # Seniority
        # -----------------------------------------------------

        seniority_value = (
            data.get(
                "seniority"
            )
        )

        if (
            seniority_value
            and seniority_value
            != "unknown"
        ):
            seniority[
                str(
                    seniority_value
                )
            ] += 1

        # -----------------------------------------------------
        # Location
        # -----------------------------------------------------

        for location in (
            data.get(
                "locations"
            )
            or []
        ):
            label = _location_label(
                location
            )

            if label:
                locations[
                    label
                ] += 1

        # -----------------------------------------------------
        # Workplace
        # -----------------------------------------------------

        workplace = (
            data.get(
                "workplace_type"
            )
        )

        if (
            workplace
            and workplace
            != "unknown"
        ):
            workplaces[
                str(workplace)
            ] += 1

        # -----------------------------------------------------
        # Domains
        # -----------------------------------------------------

        for domain in _strings(
            data.get(
                "domain_tags"
            )
        ):
            domains[
                domain
            ] += 1

    return {
        "role_counts":
            dict(roles),

        "skill_counts":
            dict(skills),

        "seniority_counts":
            dict(seniority),

        "location_counts":
            dict(locations),

        "workplace_counts":
            dict(workplaces),

        "domain_counts":
            dict(domains),
    }


def build_snapshots(
    snapshot_date: date | None = None,
) -> SnapshotSummary:

    day = (
        snapshot_date
        or date.today()
    )

    schema_version = (
        get_settings()
        .ai_classification_version
    )

    created = 0

    with get_connection() as conn:

        # -----------------------------------------------------
        # All companies
        # -----------------------------------------------------

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM companies
                ORDER BY id
                """
            )

            company_ids = [
                row[0]
                for row
                in cur.fetchall()
            ]

        # -----------------------------------------------------
        # One daily snapshot per company
        # -----------------------------------------------------

        for company_id in company_ids:

            with conn.cursor() as cur:

                # -------------------------------------------------
                # Deterministic daily activity
                # -------------------------------------------------

                cur.execute(
                    """
                    SELECT
                        (
                            SELECT COUNT(*)
                            FROM jobs
                            WHERE company_id = %s
                              AND active = TRUE
                              AND is_us_job IS TRUE
                        ),

                        COUNT(*) FILTER (
                            WHERE
                                e.event_type =
                                    'created'

                                AND

                                (
                                    e.metadata
                                    ->>'baseline'
                                )
                                IS DISTINCT FROM
                                    'true'
                        ),

                        COUNT(*) FILTER (
                            WHERE
                                e.event_type =
                                    'removed'
                        ),

                        COUNT(*) FILTER (
                            WHERE
                                e.event_type =
                                    'changed'
                        )

                    FROM job_events AS e

                    JOIN jobs AS j
                      ON j.id = e.job_id
                     AND j.is_us_job IS TRUE

                    WHERE j.company_id = %s
                      AND e.occurred_at::date = %s
                    """,
                    (
                        company_id,
                        company_id,
                        day,
                    ),
                )

                (
                    total_open,
                    new_jobs,
                    removed_jobs,
                    changed_jobs,
                ) = cur.fetchone()

            # -------------------------------------------------
            # Current semantic enrichment
            # -------------------------------------------------

            with conn.cursor(
                row_factory=dict_row
            ) as cur:

                cur.execute(
                    """
                    SELECT
                        e.standardized_title,

                        e.job_family,

                        e.skills,

                        e.required_skills,

                        e.preferred_skills,

                        e.seniority,

                        e.locations,

                        e.workplace_type,

                        COALESCE(
                            e.data->'domain_tags',
                            '[]'::jsonb
                        ) AS domain_tags

                    FROM jobs AS j

                    JOIN job_enrichments AS e
                      ON e.job_id = j.id
                     AND e.content_hash =
                            j.content_hash

                    WHERE j.company_id = %s

                      AND j.active = TRUE

                      AND j.is_us_job IS TRUE

                      AND e.schema_version = %s
                    """,
                    (
                        company_id,
                        schema_version,
                    ),
                )

                enrichment_data = list(
                    cur.fetchall()
                )

            enriched_jobs = len(
                enrichment_data
            )

            coverage = calculate_coverage(
                enriched_jobs,
                total_open,
            )

            counts = calculate_ai_counts(
                enrichment_data
            )

            # -------------------------------------------------
            # Snapshot upsert
            # -------------------------------------------------

            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO
                    company_daily_snapshots (
                        company_id,
                        snapshot_date,

                        total_open_jobs,
                        new_jobs,
                        removed_jobs,
                        changed_jobs,

                        enriched_jobs,
                        enrichment_coverage,

                        role_counts,
                        skill_counts,
                        seniority_counts,
                        location_counts,
                        workplace_counts,
                        domain_counts
                    )

                    VALUES (
                        %s,
                        %s,

                        %s,
                        %s,
                        %s,
                        %s,

                        %s,
                        %s,

                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        company_id,
                        snapshot_date
                    )

                    DO UPDATE SET

                        total_open_jobs =
                            EXCLUDED.total_open_jobs,

                        new_jobs =
                            EXCLUDED.new_jobs,

                        removed_jobs =
                            EXCLUDED.removed_jobs,

                        changed_jobs =
                            EXCLUDED.changed_jobs,

                        enriched_jobs =
                            EXCLUDED.enriched_jobs,

                        enrichment_coverage =
                            EXCLUDED.enrichment_coverage,

                        role_counts =
                            EXCLUDED.role_counts,

                        skill_counts =
                            EXCLUDED.skill_counts,

                        seniority_counts =
                            EXCLUDED.seniority_counts,

                        location_counts =
                            EXCLUDED.location_counts,

                        workplace_counts =
                            EXCLUDED.workplace_counts,

                        domain_counts =
                            EXCLUDED.domain_counts
                    """,
                    (
                        company_id,
                        day,

                        total_open,
                        new_jobs,
                        removed_jobs,
                        changed_jobs,

                        enriched_jobs,
                        coverage,

                        Jsonb(
                            counts[
                                "role_counts"
                            ]
                        ),

                        Jsonb(
                            counts[
                                "skill_counts"
                            ]
                        ),

                        Jsonb(
                            counts[
                                "seniority_counts"
                            ]
                        ),

                        Jsonb(
                            counts[
                                "location_counts"
                            ]
                        ),

                        Jsonb(
                            counts[
                                "workplace_counts"
                            ]
                        ),

                        Jsonb(
                            counts[
                                "domain_counts"
                            ]
                        ),
                    ),
                )

            created += 1

        # Publish the day atomically. If any company fails, the connection
        # context rolls back every row for this snapshot date.
        conn.commit()

    return SnapshotSummary(
        snapshot_date=day,
        snapshots_created=created,
    )
