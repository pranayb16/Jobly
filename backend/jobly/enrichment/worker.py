from __future__ import annotations



import argparse

import logging

from dataclasses import dataclass



from psycopg.rows import dict_row

from psycopg.types.json import Jsonb



from jobly.config import get_settings

from jobly.db.connection import get_connection

from jobly.enrichment.classifier import (

    GeminiUsage,

    classify_job,

)

from jobly.enrichment.deterministic import (

    extract_deterministic_fields,

)

from jobly.enrichment.input_builder import (

    build_classifier_payload,

)

from jobly.enrichment.schemas_v3 import (
    EnrichedLocationV3,
    JobEnrichmentV3,
)



from jobly.market.us_scope import classify_us_job





logger = logging.getLogger(__name__)





@dataclass(frozen=True)
class EnrichmentSummary:
    processed: int
    ai_calls: int
    completed: int
    failed: int
    stale: int
    skipped_non_us: int
    backlog: int

    input_tokens: int
    output_tokens: int
    thought_tokens: int
    cached_tokens: int
    total_tokens: int

    model_counts: dict[str, int]





def recover_stale_queue(

    conn,

) -> None:

    settings = get_settings()



    with conn.cursor() as cur:

        cur.execute(

            """

            UPDATE enrichment_queue

            SET

                status = CASE

                    WHEN attempts >= %s

                    THEN 'failed'

                    ELSE 'pending'

                END,



                started_at = NULL,



                last_error = COALESCE(

                    last_error,

                    'worker_timeout'

                )



            WHERE status = 'processing'



              AND started_at

                    < NOW() - INTERVAL '15 minutes'

            """,

            (

                settings.ai_max_attempts,

            ),

        )



    conn.commit()





def count_backlog(

    conn,

) -> int:

    with conn.cursor() as cur:

        cur.execute(

            """

            SELECT COUNT(*)

            FROM enrichment_queue

            WHERE status = 'pending'

            """

        )



        return cur.fetchone()[0]


def claim_next_queue_item(
    conn,
    excluded_queue_ids: set[int] | None = None,
) -> dict | None:
    settings = get_settings()

    excluded_queue_ids = (
        excluded_queue_ids
        or set()
    )

    with conn.cursor(
        row_factory=dict_row
    ) as cur:

        if excluded_queue_ids:

            cur.execute(
                """
                SELECT
                    id,
                    job_id,
                    content_hash,
                    priority,
                    reason,
                    attempts

                FROM enrichment_queue

                WHERE status = 'pending'
                  AND attempts < %s
                  AND NOT (
                      id = ANY(%s::bigint[])
                  )

                ORDER BY
                    priority ASC,
                    created_at ASC,
                    id ASC

                FOR UPDATE SKIP LOCKED

                LIMIT 1
                """,
                (
                    settings.ai_max_attempts,
                    list(excluded_queue_ids),
                ),
            )

        else:

            cur.execute(
                """
                SELECT
                    id,
                    job_id,
                    content_hash,
                    priority,
                    reason,
                    attempts

                FROM enrichment_queue

                WHERE status = 'pending'
                  AND attempts < %s

                ORDER BY
                    priority ASC,
                    created_at ASC,
                    id ASC

                FOR UPDATE SKIP LOCKED

                LIMIT 1
                """,
                (
                    settings.ai_max_attempts,
                ),
            )

        queue_item = cur.fetchone()

        if queue_item is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE enrichment_queue

            SET
                status = 'processing',
                started_at = NOW(),
                attempts = attempts + 1,
                last_error = NULL

            WHERE id = %s

            RETURNING attempts
            """,
            (
                queue_item["id"],
            ),
        )

        queue_item["attempts"] = (
            cur.fetchone()["attempts"]
        )

        cur.execute(
            """
            SELECT
                id,
                external_job_id,
                provider,
                company,
                title,
                location,
                employment_type,
                workplace_type,
                posted_at,
                posted_at_source,
                description_text,
                raw_payload,
                content_hash

            FROM jobs

            WHERE id = %s
            """,
            (
                queue_item["job_id"],
            ),
        )

        job = cur.fetchone()

    conn.commit()

    if job is None:
        return None

    return {
        **job,

        "queue_id":
            queue_item["id"],

        "queue_hash":
            queue_item["content_hash"],

        "queue_attempts":
            queue_item["attempts"],

        "queue_reason":
            queue_item["reason"],

        "queue_priority":
            queue_item["priority"],
    }


def _complete_queue(

    conn,

    queue_id: int,

    note: str | None = None,

) -> None:

    with conn.cursor() as cur:

        cur.execute(

            """

            UPDATE enrichment_queue

            SET

                status = 'completed',

                completed_at = NOW(),

                started_at = NULL,

                last_error = %s



            WHERE id = %s

            """,

            (

                note,

                queue_id,

            ),

        )



    conn.commit()





def _mark_non_us(

    conn,

    item: dict,

    reason: str,

) -> None:

    with conn.cursor() as cur:

        cur.execute(

            """

            UPDATE jobs

            SET

                is_us_job = FALSE,

                us_location_reason = %s,

                classification_status =

                    'skipped_non_us',

                classification_started_at = NULL,

                classification_error = NULL



            WHERE id = %s

              AND content_hash = %s

            """,

            (

                reason,

                item["id"],

                item["queue_hash"],

            ),

        )



        cur.execute(

            """

            UPDATE enrichment_queue

            SET

                status = 'completed',

                completed_at = NOW(),

                started_at = NULL



            WHERE id = %s

            """,

            (

                item["queue_id"],

            ),

        )



    conn.commit()





def _unique_strings(

    values: list[str],

) -> list[str]:

    result: list[str] = []



    for value in values:

        cleaned = " ".join(

            value.strip().split()

        )



        if (

            cleaned

            and cleaned not in result

        ):

            result.append(

                cleaned

            )



    return result




def _location_dict(

    location,

) -> dict:

    data = location.model_dump()



    state = data.get(

        "state",

        data.get("region"),

    )



    return {

        "city":

            data.get("city"),



        "state":

            state,



        "state_code":

            data.get("state_code"),



        "country":

            data.get("country"),



        "country_code":

            data.get("country_code"),

    }

def _normalize_employment_type(
    value,
) -> str | None:

    if not value:
        return None

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )

    mapping = {
        "fulltime": "full_time",
        "parttime": "part_time",
        "contract": "contract",
        "contractor": "contract",
        "temporary": "temporary",
        "temp": "temporary",
        "intern": "internship",
        "internship": "internship",
        "seasonal": "seasonal",
    }

    return mapping.get(
        normalized
    )


def _normalize_workplace_type(
    value,
) -> str | None:

    if not value:
        return None

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )

    mapping = {
        "remote": "remote",
        "hybrid": "hybrid",
        "onsite": "onsite",
        "onlocation": "onsite",
        "inoffice": "onsite",
        "office": "onsite",
        "flexible": "flexible",
    }

    return mapping.get(
        normalized
    )


def _country_code(
    country: str | None,
) -> str | None:

    if not country:
        return None

    normalized = (
        country
        .strip()
        .lower()
    )

    if normalized in {
        "united states",
        "united states of america",
        "usa",
        "us",
        "u.s.",
    }:
        return "US"

    return None


def _simple_location_label(
    value: str | None,
) -> str | None:

    if not value:
        return None

    cleaned = " ".join(
        str(value)
        .strip()
        .split()
    )

    if not cleaned:
        return None

    if cleaned.lower() in {
        "remote",
        "hybrid",
        "onsite",
        "on-site",
        "anywhere",
    }:
        return None

    return cleaned


def _ashby_ats_locations(
    item: dict,
) -> list[EnrichedLocationV3]:

    raw = (
        item.get("raw_payload")
        or {}
    )

    if (
        str(item.get("provider") or "")
        .lower()
        != "ashby"
    ):
        return []

    result: list[
        EnrichedLocationV3
    ] = []


    def add_location(
        *,
        label=None,
        address=None,
    ) -> None:

        address = (
            address
            if isinstance(address, dict)
            else {}
        )

        postal = (
            address.get(
                "postalAddress",
                address,
            )
        )

        if not isinstance(
            postal,
            dict,
        ):
            postal = {}

        city = (
            _simple_location_label(
                label
            )
            or postal.get(
                "addressLocality"
            )
        )

        state = postal.get(
            "addressRegion"
        )

        country = postal.get(
            "addressCountry"
        )

        if not any(
            (
                city,
                state,
                country,
            )
        ):
            return

        result.append(
            EnrichedLocationV3(
                city=city,
                state=state,
                country=country,
                country_code=(
                    _country_code(
                        country
                    )
                ),
            )
        )


    # Primary Ashby location.
    add_location(
        label=item.get("location"),
        address=raw.get("address"),
    )


    # Ashby can have multiple secondary locations.
    for secondary in raw.get(
        "secondaryLocations",
        [],
    ):

        if not isinstance(
            secondary,
            dict,
        ):
            continue

        add_location(
            label=secondary.get(
                "location"
            ),
            address=secondary.get(
                "address"
            ),
        )

    return result


def _locations_match(
    left: EnrichedLocationV3,
    right: EnrichedLocationV3,
) -> bool:

    left_city = (
        left.city or ""
    ).strip().lower()

    right_city = (
        right.city or ""
    ).strip().lower()

    if (
        left_city
        and right_city
        and left_city != right_city
    ):
        return False

    left_state = (
        left.state or ""
    ).strip().lower()

    right_state = (
        right.state or ""
    ).strip().lower()

    if (
        left_state
        and right_state
        and left_state != right_state
    ):
        return False

    left_country = (
        left.country or ""
    ).strip().lower()

    right_country = (
        right.country or ""
    ).strip().lower()

    if (
        left_country
        and right_country
        and left_country != right_country
    ):
        return False

    return bool(
        left_city
        or right_city
        or left_state
        or right_state
        or left_country
        or right_country
    )


def _merge_locations(
    ai_locations: list[EnrichedLocationV3],
    ats_locations: list[EnrichedLocationV3],
) -> list[EnrichedLocationV3]:

    result = list(
        ai_locations
    )

    for ats_location in ats_locations:

        duplicate = any(
            _locations_match(
                existing,
                ats_location,
            )
            for existing in result
        )

        if not duplicate:
            result.append(
                ats_location
            )

    return result



def _build_canonical_projection(

    classification,

) -> dict:

    if isinstance(

        classification,

        JobEnrichmentV3,

    ):

        required_skills = [
            skill.name
            for skill
            in classification.skills
            if skill.requirement == "required"
        ]



        preferred_skills = [
            skill.name
            for skill
            in classification.skills
            if skill.requirement == "preferred"
        ]



        skills = [
            skill.name
            for skill
            in classification.skills
        ]



        certifications = [
            certification.name
            for certification
            in classification.certifications
        ]



        locations = [

            _location_dict(location)

            for location

            in classification.locations

        ]



        primary_location = (

            locations[0]

            if locations

            else {}

        )



        return {

            "standardized_title":

                classification.standardized_title,



            "job_family":

                classification.job_family,



            "job_subfamily":

                classification.job_subfamily,



            "related_roles": [],



            # Removed from the AI schema.

            "role_track":

                "unknown",



            "seniority":

                classification.seniority,



            # Removed from the AI schema.

            "leadership_level":

                "unknown",



            # Removed from the AI schema.

            "role_keywords":

                [],



            # Removed from the AI schema.

            "responsibility_tags":

                [],



            "skills":

                skills,



            # Derived for backward compatibility.

            "required_skills":

                required_skills,



            # Derived for backward compatibility.

            "preferred_skills":

                preferred_skills,



            # Removed from the AI schema.

            "soft_skills":

                [],



            "skill_count":

                len(skills),



            "years_experience_min":

                classification.years_experience_min,



            "years_experience_max":

                classification.years_experience_max,



            # Removed from v3 AI extraction.

            "education_required":

                "unknown",



            # Removed from v3 AI extraction.

            "education_preferred":

                "unknown",



            "education_level":

                classification.education_level,



            "education_fields":

                classification.education_fields,



            # Compact dictionary is retained in data JSON.

            # Existing canonical field receives names only.

            "certifications":

                certifications,



            "locations":

                locations,



            # Removed from v3.

            "preferred_locations":

                [],



            "city":

                primary_location.get("city"),



            "state":

                primary_location.get("state"),



            "state_code":

                primary_location.get(

                    "state_code"

                ),



            "country":

                primary_location.get("country"),



            "country_code":

                primary_location.get(

                    "country_code"

                ),



            "workplace_type":

                classification.workplace_type,



            "relocation_available": None,



            "employment_type":

                classification.employment_type,



            "salary_min":

                classification.salary_min,



            "salary_max":

                classification.salary_max,



            "salary_currency":

                classification.salary_currency,



            "salary_period":

                classification.salary_period,



            "visa_sponsorship":

                classification.visa_sponsorship,



            "work_authorization_required":

                classification.work_authorization_required,



            "citizenship_requirement":

                classification.citizenship_requirement,



            "security_clearance_required":

                classification.security_clearance_required,



            "security_clearance_level":

                classification.security_clearance_level,



            "confidence":

                classification.confidence,

        }



    # Existing v2 behavior.

    skills = _unique_strings(

        classification.required_skills

        + classification.preferred_skills

        + classification.soft_skills

    )



    certifications = _unique_strings(

        classification.required_certifications

        + classification.preferred_certifications

    )



    locations = [

        _location_dict(location)

        for location

        in classification.locations

    ]



    primary_location = (

        locations[0]

        if locations

        else {}

    )



    return {

        "standardized_title":

            classification.standardized_title,



        "job_family":

            classification.job_family,



        "job_subfamily":

            classification.job_subfamily,



        "related_roles":

            classification.related_roles,



        "role_track":

            classification.role_track,



        "seniority":

            classification.seniority,



        "leadership_level":

            classification.leadership_level,



        "role_keywords":

            getattr(

                classification,

                "role_keywords",

                [],

            ),



        "responsibility_tags":

            classification.responsibility_tags,



        "skills":

            skills,



        "required_skills":

            classification.required_skills,



        "preferred_skills":

            classification.preferred_skills,



        "soft_skills":

            classification.soft_skills,



        "skill_count":

            len(skills),



        "years_experience_min":

            classification.years_experience_min,



        "years_experience_max":

            classification.years_experience_max,



        "education_required":

            classification.education_required,



        "education_preferred":

            classification.education_preferred,



        "education_level":

            classification.education_level,



        "education_fields":

            classification.education_fields,



        "certifications":

            certifications,



        "locations":

            locations,



        "preferred_locations": [

            _location_dict(location)

            for location

            in getattr(

                classification,

                "preferred_locations",

                [],

            )

        ],



        "city":

            primary_location.get("city"),



        "state":

            primary_location.get("state"),



        "state_code":

            primary_location.get(

                "state_code"

            ),



        "country":

            primary_location.get("country"),



        "country_code":

            primary_location.get(

                "country_code"

            ),



        "workplace_type":

            classification.workplace_type,



        "relocation_available":

            classification.relocation_available,



        "employment_type":

            classification.employment_type,



        "salary_min":

            classification.salary_min,



        "salary_max":

            classification.salary_max,



        "salary_currency":

            classification.salary_currency,



        "salary_period":

            classification.salary_period,



        "visa_sponsorship":

            classification.visa_sponsorship,



        "work_authorization_required":

            classification.work_authorization_required,



        "citizenship_requirement":

            classification.citizenship_requirement,



        "security_clearance_required":

            classification.security_clearance_required,



        "security_clearance_level":

            classification.security_clearance_level,



        "confidence":

            classification.confidence,

    }





def _legacy_projection(

    classification: JobEnrichmentV3,

) -> dict:

    canonical = _build_canonical_projection(

        classification

    )



    ai_locations = [

        {

            "city":

                location.city,



            "state":

                location.state,



            "state_code":

                location.state_code,



            "country":

                location.country,



            "country_code":

                location.country_code,



            "remote":

                (

                    classification.workplace_type

                    == "remote"

                ),

        }



        for location

        in classification.locations

    ]



    return {

        "job_family":

            classification.job_family,



        "job_subfamily":

            classification.job_subfamily,



        "related_roles": [],



        "skills":

            canonical["skills"],



        "seniority":

            classification.seniority,



        "years_min":

            classification.years_experience_min,



        "years_max":

            classification.years_experience_max,



        "locations":

            ai_locations,



        "confidence":

            classification.confidence,

    }





def save_success(

    conn,

    item: dict,

    classification: JobEnrichmentV3,

    usage: GeminiUsage | None = None,

) -> bool:

    settings = get_settings()



    usage = usage or GeminiUsage()



    with conn.cursor() as cur:

        cur.execute(

            """

            SELECT content_hash

            FROM jobs

            WHERE id = %s

            FOR UPDATE

            """,

            (

                item["id"],

            ),

        )



        current = cur.fetchone()



        if (

            current is None

            or current[0]

            != item["queue_hash"]

        ):

            cur.execute(

                """

                UPDATE enrichment_queue

                SET

                    status = 'completed',

                    completed_at = NOW(),

                    started_at = NULL,

                    last_error =

                        'stale_content_hash'



                WHERE id = %s

                """,

                (

                    item["queue_id"],

                ),

            )



            conn.commit()



            return False



        data = classification.model_dump(

            mode="json"

        )



        canonical = (

            _build_canonical_projection(

                classification

            )

        )



        legacy = (

            _legacy_projection(

                classification

            )

        )



        params = {

            "job_id":

                item["id"],



            "content_hash":

                item["queue_hash"],



            "schema_version":

                settings.ai_classification_version,



            "model":
                (
                usage.model
                or settings.openrouter_paid_model
            ),



            "prompt_version":

                settings.ai_prompt_version,



            "data":

                Jsonb(data),



            "confidence":

                canonical["confidence"],



            "standardized_title":

                canonical["standardized_title"],



            "job_family":

                canonical["job_family"],



            "job_subfamily":

                canonical["job_subfamily"],



            "related_roles":

                [],



            "role_track":

                canonical["role_track"],



            "seniority":

                canonical["seniority"],



            "leadership_level":

                canonical["leadership_level"],



            "role_keywords":

                Jsonb(

                    canonical["role_keywords"]

                ),



            "responsibility_tags":

                Jsonb(

                    canonical[

                        "responsibility_tags"

                    ]

                ),



            "skills":

                Jsonb(

                    canonical["skills"]

                ),



            "required_skills":

                Jsonb(

                    canonical[

                        "required_skills"

                    ]

                ),



            "preferred_skills":

                Jsonb(

                    canonical[

                        "preferred_skills"

                    ]

                ),



            "soft_skills":

                Jsonb(

                    canonical[

                        "soft_skills"

                    ]

                ),



            "skill_count":

                canonical["skill_count"],



            "years_experience_min":

                canonical[

                    "years_experience_min"

                ],



            "years_experience_max":

                canonical[

                    "years_experience_max"

                ],



            "education_required":

                canonical[

                    "education_required"

                ],



            "education_preferred":

                canonical[

                    "education_preferred"

                ],



            "education_level":

                canonical[

                    "education_level"

                ],



            "education_fields":

                Jsonb(

                    canonical[

                        "education_fields"

                    ]

                ),



            "certifications":

                Jsonb(

                    canonical[

                        "certifications"

                    ]

                ),



            "locations":

                Jsonb(

                    canonical["locations"]

                ),



            "preferred_locations":

                Jsonb(

                    canonical[

                        "preferred_locations"

                    ]

                ),



            "city":

                canonical["city"],



            "state":

                canonical["state"],



            "state_code":

                canonical["state_code"],



            "country":

                canonical["country"],



            "country_code":

                canonical["country_code"],



            "workplace_type":

                canonical["workplace_type"],



            "relocation_available":

                None,



            "employment_type":

                canonical["employment_type"],



            "salary_min":

                canonical["salary_min"],



            "salary_max":

                canonical["salary_max"],



            "salary_currency":

                canonical["salary_currency"],



            "salary_period":

                canonical["salary_period"],



            "visa_sponsorship":

                canonical["visa_sponsorship"],



            "work_authorization_required":

                canonical[

                    "work_authorization_required"

                ],



            "citizenship_requirement":

                canonical[

                    "citizenship_requirement"

                ],



            "security_clearance_required":

                canonical[

                    "security_clearance_required"

                ],



            "security_clearance_level":

                canonical[

                    "security_clearance_level"

                ],



            # Gemini usage

            "gemini_interaction_id":

                usage.interaction_id,



            "input_tokens":

                usage.input_tokens,



            "output_tokens":

                usage.output_tokens,



            "thought_tokens":

                usage.thought_tokens,



            "cached_tokens":

                usage.cached_tokens,



            "total_tokens":

                usage.total_tokens,

        }



        cur.execute(

            """

            INSERT INTO job_enrichments (

                job_id,

                content_hash,

                schema_version,

                model,

                prompt_version,

                data,

                confidence,



                standardized_title,

                job_family,

                job_subfamily,

                related_roles,

                role_track,

                seniority,

                leadership_level,

                role_keywords,

                responsibility_tags,



                skills,

                required_skills,

                preferred_skills,

                soft_skills,

                skill_count,



                years_experience_min,

                years_experience_max,



                education_required,

                education_preferred,

                education_level,

                education_fields,

                certifications,



                locations,

                preferred_locations,

                city,

                state,

                state_code,

                country,

                country_code,



                workplace_type,

                relocation_available,

                employment_type,



                salary_min,

                salary_max,

                salary_currency,

                salary_period,



                visa_sponsorship,

                work_authorization_required,

                citizenship_requirement,

                security_clearance_required,

                security_clearance_level,



                gemini_interaction_id,

                input_tokens,

                output_tokens,

                thought_tokens,

                cached_tokens,

                total_tokens

            )



            VALUES (

                %(job_id)s,

                %(content_hash)s,

                %(schema_version)s,

                %(model)s,

                %(prompt_version)s,

                %(data)s,

                %(confidence)s,



                %(standardized_title)s,

                %(job_family)s,

                %(job_subfamily)s,

                %(related_roles)s,

                %(role_track)s,

                %(seniority)s,

                %(leadership_level)s,

                %(role_keywords)s,

                %(responsibility_tags)s,



                %(skills)s,

                %(required_skills)s,

                %(preferred_skills)s,

                %(soft_skills)s,

                %(skill_count)s,



                %(years_experience_min)s,

                %(years_experience_max)s,



                %(education_required)s,

                %(education_preferred)s,

                %(education_level)s,

                %(education_fields)s,

                %(certifications)s,



                %(locations)s,

                %(preferred_locations)s,

                %(city)s,

                %(state)s,

                %(state_code)s,

                %(country)s,

                %(country_code)s,



                %(workplace_type)s,

                %(relocation_available)s,

                %(employment_type)s,



                %(salary_min)s,

                %(salary_max)s,

                %(salary_currency)s,

                %(salary_period)s,



                %(visa_sponsorship)s,

                %(work_authorization_required)s,

                %(citizenship_requirement)s,

                %(security_clearance_required)s,

                %(security_clearance_level)s,



                %(gemini_interaction_id)s,

                %(input_tokens)s,

                %(output_tokens)s,

                %(thought_tokens)s,

                %(cached_tokens)s,

                %(total_tokens)s

            )



            ON CONFLICT (

                job_id,

                content_hash,

                schema_version

            )



            DO UPDATE SET

                model =

                    EXCLUDED.model,



                prompt_version =

                    EXCLUDED.prompt_version,



                data =

                    EXCLUDED.data,



                confidence =

                    EXCLUDED.confidence,



                standardized_title =

                    EXCLUDED.standardized_title,



                job_family =

                    EXCLUDED.job_family,



                job_subfamily =

                    EXCLUDED.job_subfamily,



                related_roles =

                    EXCLUDED.related_roles,



                role_track =

                    EXCLUDED.role_track,



                seniority =

                    EXCLUDED.seniority,



                leadership_level =

                    EXCLUDED.leadership_level,



                role_keywords =

                    EXCLUDED.role_keywords,



                responsibility_tags =

                    EXCLUDED.responsibility_tags,



                skills =

                    EXCLUDED.skills,



                required_skills =

                    EXCLUDED.required_skills,



                preferred_skills =

                    EXCLUDED.preferred_skills,



                soft_skills =

                    EXCLUDED.soft_skills,



                skill_count =

                    EXCLUDED.skill_count,



                years_experience_min =

                    EXCLUDED.years_experience_min,



                years_experience_max =

                    EXCLUDED.years_experience_max,



                education_required =

                    EXCLUDED.education_required,



                education_preferred =

                    EXCLUDED.education_preferred,



                education_level =

                    EXCLUDED.education_level,



                education_fields =

                    EXCLUDED.education_fields,



                certifications =

                    EXCLUDED.certifications,



                locations =

                    EXCLUDED.locations,



                preferred_locations =

                    EXCLUDED.preferred_locations,



                city =

                    EXCLUDED.city,



                state =

                    EXCLUDED.state,



                state_code =

                    EXCLUDED.state_code,



                country =

                    EXCLUDED.country,



                country_code =

                    EXCLUDED.country_code,



                workplace_type =

                    EXCLUDED.workplace_type,



                relocation_available =

                    EXCLUDED.relocation_available,



                employment_type =

                    EXCLUDED.employment_type,



                salary_min =

                    EXCLUDED.salary_min,



                salary_max =

                    EXCLUDED.salary_max,



                salary_currency =

                    EXCLUDED.salary_currency,



                salary_period =

                    EXCLUDED.salary_period,



                visa_sponsorship =

                    EXCLUDED.visa_sponsorship,



                work_authorization_required =

                    EXCLUDED.work_authorization_required,



                citizenship_requirement =

                    EXCLUDED.citizenship_requirement,



                security_clearance_required =

                    EXCLUDED.security_clearance_required,



                security_clearance_level =

                    EXCLUDED.security_clearance_level,



                gemini_interaction_id =

                    EXCLUDED.gemini_interaction_id,



                input_tokens =

                    EXCLUDED.input_tokens,



                output_tokens =

                    EXCLUDED.output_tokens,



                thought_tokens =

                    EXCLUDED.thought_tokens,



                cached_tokens =

                    EXCLUDED.cached_tokens,



                total_tokens =

                    EXCLUDED.total_tokens,



                created_at =

                    NOW()

            """,

            params,

        )



        # Temporary compatibility update for the old jobs table.

        cur.execute(

            """

            UPDATE jobs

            SET

                job_family = %s,

                job_subfamily = %s,

                related_roles = %s,

                skills = %s,

                seniority = %s,

                years_experience_min = %s,

                years_experience_max = %s,

                ai_locations = %s,

                classification_confidence = %s,



                classification_status = 'ready',



                classification_version = %s,



                classified_at = NOW(),



                classified_content_hash =

                    content_hash,



                classification_started_at =

                    NULL,



                classification_error =

                    NULL,



                is_us_job = TRUE



            WHERE id = %s

              AND content_hash = %s

            """,

            (

                legacy["job_family"],

                legacy["job_subfamily"],



                Jsonb(

                    legacy["related_roles"]

                ),



                Jsonb(

                    legacy["skills"]

                ),



                legacy["seniority"],

                legacy["years_min"],

                legacy["years_max"],



                Jsonb(

                    legacy["locations"]

                ),



                legacy["confidence"],



                settings.ai_classification_version,



                item["id"],

                item["queue_hash"],

            ),

        )



        cur.execute(

            """

            UPDATE enrichment_queue

            SET

                status = 'completed',

                completed_at = NOW(),

                started_at = NULL,

                last_error = NULL



            WHERE id = %s

            """,

            (

                item["queue_id"],

            ),

        )



    conn.commit()



    return True





def save_failure(

    conn,

    item: dict,

    error: Exception,

) -> bool:

    settings = get_settings()



    terminal = (

        item["queue_attempts"]

        >= settings.ai_max_attempts

    )



    error_message = str(

        error

    )[:2000]



    with conn.cursor() as cur:

        cur.execute(

            """

            UPDATE enrichment_queue

            SET

                status = %s,

                started_at = NULL,

                last_error = %s,



                completed_at = CASE

                    WHEN %s

                    THEN NOW()

                    ELSE NULL

                END



            WHERE id = %s

            """,

            (

                (

                    "failed"

                    if terminal

                    else "pending"

                ),



                error_message,

                terminal,

                item["queue_id"],

            ),

        )



        cur.execute(

            """

            UPDATE jobs

            SET

                classification_status = %s,

                classification_started_at = NULL,



                classification_attempts =

                    classification_attempts + 1,



                classification_error = %s



            WHERE id = %s

              AND content_hash = %s

            """,

            (

                (

                    "failed"

                    if terminal

                    else "pending"

                ),



                error_message,

                item["id"],

                item["queue_hash"],

            ),

        )



    conn.commit()



    return terminal




def process_item(
    conn,
    item: dict,
) -> tuple[str, GeminiUsage | None]:

    if (
        item["content_hash"]
        != item["queue_hash"]
    ):

        _complete_queue(
            conn,
            item["queue_id"],
            "stale_content_hash",
        )

        return "stale", None


    decision = classify_us_job(
        provider=item["provider"],
        location=item["location"],
        raw=item["raw_payload"],
    )


    if not decision.eligible:

        _mark_non_us(
            conn,
            item,
            decision.reason,
        )

        return "skipped_non_us", None


    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE jobs
            SET
                is_us_job = TRUE,
                us_location_reason = %s,
                classification_status = 'processing',
                classification_started_at = NOW()
            WHERE id = %s
              AND content_hash = %s
            """,
            (
                decision.reason,
                item["id"],
                item["queue_hash"],
            ),
        )

    conn.commit()


    # --------------------------------------------------------
    # DETERMINISTIC ATS FACTS
    # --------------------------------------------------------

    structured_context = (
        extract_deterministic_fields(
            item
        )
    )


    # --------------------------------------------------------
    # MINIMAL AI PAYLOAD
    # --------------------------------------------------------

    payload = build_classifier_payload(
        item
    )

    # IMPORTANT:
    # Do NOT add trusted_structured_context to the AI payload.
    #
    # AI still sees the job description and can extract
    # multiple locations explicitly stated in the posting.


    result = classify_job(
        payload,
        schema_version=(
            get_settings()
            .ai_classification_version
        ),
    )


    # --------------------------------------------------------
    # TRUST ATS EMPLOYMENT TYPE
    # --------------------------------------------------------

    employment_type = (
        _normalize_employment_type(
            structured_context.get(
                "employment_type"
            )
        )
    )

    if employment_type:
        result.classification.employment_type = (
            employment_type
        )


    # --------------------------------------------------------
    # TRUST ATS WORKPLACE TYPE
    # --------------------------------------------------------

    workplace_type = (
        _normalize_workplace_type(
            structured_context.get(
                "workplace_type"
            )
        )
    )

    if workplace_type:
        result.classification.workplace_type = (
            workplace_type
        )


    # --------------------------------------------------------
    # MERGE AI + ATS LOCATIONS
    #
    # AI locations are retained because the posting may name
    # multiple locations.
    #
    # ATS locations are added when AI missed them.
    # --------------------------------------------------------

    ats_locations = (
        _ashby_ats_locations(
            item
        )
    )

    result.classification.locations = (
        _merge_locations(
            result.classification.locations,
            ats_locations,
        )
    )


    # --------------------------------------------------------
    # CITIZENSHIP SAFETY CHECK
    # --------------------------------------------------------

    description_lower = (
        item.get(
            "description_text"
        )
        or ""
    ).lower()

    citizenship_phrases = (
        "u.s. citizen",
        "us citizen",
        "united states citizen",
        "must be a citizen",
        "citizenship required",
    )

    if not any(
        phrase in description_lower
        for phrase in citizenship_phrases
    ):
        result.classification.citizenship_requirement = (
            None
        )


    saved = save_success(
        conn,
        item,
        result.classification,
        result.usage,
    )


    if not saved:
        return (
            "stale",
            result.usage,
        )


    return (
        "completed",
        result.usage,
    )




def run_enrichment(
    limit: int | None = None,
    pipeline_run_id: int | None = None,
) -> EnrichmentSummary:

    limit = (
        limit
        or get_settings().ai_enrichment_limit
    )

    if limit < 1:
        raise ValueError(
            "enrichment limit must be at least 1"
        )

    # Queue rows examined.
    processed = 0

    # Actual AI classifications completed.
    ai_calls = 0

    completed = 0
    failed = 0
    stale = 0
    skipped_non_us = 0

    input_tokens = 0
    output_tokens = 0
    thought_tokens = 0
    cached_tokens = 0
    total_tokens = 0

    model_counts: dict[str, int] = {}

    attempted_queue_ids: set[int] = set()
    with get_connection() as conn:

        recover_stale_queue(conn)

        # IMPORTANT:
        # limit now controls actual AI calls,
        # not queue items.
        while ai_calls < limit:

            item = claim_next_queue_item(
                conn,
                attempted_queue_ids,
            )

            if item is None:
                break

            attempted_queue_ids.add(
                item["queue_id"]
            )


            processed += 1

            try:

                result, usage = process_item(
                    conn,
                    item,
                )

                completed += int(
                    result in {
                        "completed",
                        "skipped_non_us",
                    }
                )

                stale += int(
                    result == "stale"
                )

                skipped_non_us += int(
                    result == "skipped_non_us"
                )

                # usage exists only when the job
                # actually reached the AI classifier.
                if usage is not None:

                    ai_calls += 1

                    input_tokens += (
                        usage.input_tokens
                    )

                    output_tokens += (
                        usage.output_tokens
                    )

                    thought_tokens += (
                        usage.thought_tokens
                    )

                    cached_tokens += (
                        usage.cached_tokens
                    )

                    total_tokens += (
                        usage.total_tokens
                    )

                    model_name = (
                        usage.model
                        or "unknown"
                    )

                    model_counts[
                        model_name
                    ] = (
                        model_counts.get(
                            model_name,
                            0,
                        )
                        + 1
                    )

            except Exception as exc:

                logger.exception(
                    "enrichment_failed "
                    "queue_id=%s job_id=%s",
                    item["queue_id"],
                    item["id"],
                )

                save_failure(
                    conn,
                    item,
                    exc,
                )

                failed += 1

        backlog = count_backlog(conn)

    return EnrichmentSummary(
        processed=processed,
        ai_calls=ai_calls,
        completed=completed,
        failed=failed,
        stale=stale,
        skipped_non_us=skipped_non_us,
        backlog=backlog,

        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thought_tokens=thought_tokens,
        cached_tokens=cached_tokens,
        total_tokens=total_tokens,

        model_counts=model_counts,
    )





def main() -> None:

    parser = argparse.ArgumentParser(

        description=(

            "Process the priority enrichment queue."

        )

    )



    parser.add_argument(

        "--limit",

        type=int,

        default=(

            get_settings()

            .ai_enrichment_limit

        ),

    )



    args = parser.parse_args()



    summary = run_enrichment(

        args.limit

    )



    print(
        "Enrichment complete | "
        f"processed={summary.processed} | "
        f"ai_calls={summary.ai_calls} | "
        f"completed={summary.completed} | "
        f"failed={summary.failed} | "
        f"stale={summary.stale} | "
        f"skipped_non_us={summary.skipped_non_us} | "
        f"backlog={summary.backlog} | "
        f"input_tokens={summary.input_tokens} | "
        f"output_tokens={summary.output_tokens} | "
        f"thought_tokens={summary.thought_tokens} | "
        f"cached_tokens={summary.cached_tokens} | "
        f"total_tokens={summary.total_tokens}"
    )


if __name__ == "__main__":

    main()