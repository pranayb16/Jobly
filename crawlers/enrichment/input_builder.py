import hashlib
import json
from typing import Any


def unique_strings(values):
    result = []

    for value in values:

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value not in result:
            result.append(value)

    return result


def format_postal_address(
    address: dict | None,
) -> str | None:

    if not isinstance(address, dict):
        return None

    postal = address.get(
        "postalAddress",
        address,
    )

    if not isinstance(postal, dict):
        return None

    parts = [
        postal.get("addressLocality"),
        postal.get("addressRegion"),
        postal.get("addressCountry"),
    ]

    parts = [
        str(part).strip()
        for part in parts
        if part
    ]

    if not parts:
        return None

    return ", ".join(parts)


def extract_greenhouse_context(
    raw: dict,
) -> dict:

    departments = []

    for department in raw.get(
        "departments",
        [],
    ):
        if isinstance(department, dict):
            name = department.get("name")

            if name:
                departments.append(name)

    locations = []

    location = raw.get("location")

    if isinstance(location, dict):
        if location.get("name"):
            locations.append(
                location["name"]
            )

    offices = []

    for office in raw.get(
        "offices",
        [],
    ):
        if not isinstance(office, dict):
            continue

        office_name = office.get("name")
        office_location = office.get(
            "location"
        )

        if office_name:
            offices.append(office_name)

        if office_location:
            locations.append(
                office_location
            )

    return {
        "departments": unique_strings(
            departments
        ),

        "teams": [],

        "locations": unique_strings(
            locations
        ),

        "offices": unique_strings(
            offices
        ),
    }


def extract_ashby_context(
    raw: dict,
) -> dict:

    locations = []

    if raw.get("location"):
        locations.append(
            raw["location"]
        )

    address = format_postal_address(
        raw.get("address")
    )

    if address:
        locations.append(address)

    for secondary in raw.get(
        "secondaryLocations",
        [],
    ):

        if not isinstance(
            secondary,
            dict,
        ):
            continue

        location = secondary.get(
            "location"
        )

        if location:
            locations.append(location)

        address = format_postal_address(
            secondary.get("address")
        )

        if address:
            locations.append(address)

    departments = []

    if raw.get("department"):
        departments.append(
            raw["department"]
        )

    teams = []

    if raw.get("team"):
        teams.append(
            raw["team"]
        )

    return {
        "departments": unique_strings(
            departments
        ),

        "teams": unique_strings(
            teams
        ),

        "locations": unique_strings(
            locations
        ),

        "offices": [],
    }


def extract_lever_context(
    raw: dict,
) -> dict:

    categories = raw.get(
        "categories",
        {},
    )

    if not isinstance(
        categories,
        dict,
    ):
        categories = {}

    locations = []

    if categories.get("location"):
        locations.append(
            categories["location"]
        )

    all_locations = categories.get(
        "allLocations",
        [],
    )

    if isinstance(
        all_locations,
        list,
    ):
        locations.extend(
            all_locations
        )

    departments = []

    if categories.get("department"):
        departments.append(
            categories["department"]
        )

    teams = []

    if categories.get("team"):
        teams.append(
            categories["team"]
        )

    return {
        "departments": unique_strings(
            departments
        ),

        "teams": unique_strings(
            teams
        ),

        "locations": unique_strings(
            locations
        ),

        "offices": [],
    }


def extract_structured_context(
    provider: str,
    raw: dict | None,
) -> dict:

    raw = raw or {}

    provider = provider.lower()

    if provider == "greenhouse":
        return extract_greenhouse_context(
            raw
        )

    if provider == "ashby":
        return extract_ashby_context(
            raw
        )

    if provider == "lever":
        return extract_lever_context(
            raw
        )

    return {
        "departments": [],
        "teams": [],
        "locations": [],
        "offices": [],
    }


def build_classifier_payload(
    row: dict[str, Any],
) -> dict:

    raw = row.get("raw_payload") or {}

    if isinstance(raw, str):
        raw = json.loads(raw)

    structured_context = (
        extract_structured_context(
            row["provider"],
            raw,
        )
    )

    return {
        "original_title": row["title"],

        "company": row.get("company"),

        "provider": row["provider"],

        "department": (
            structured_context[
                "departments"
            ]
        ),

        "team": (
            structured_context[
                "teams"
            ]
        ),

        "primary_location": (
            row.get("location")
        ),

        "structured_locations": (
            structured_context[
                "locations"
            ]
        ),

        "offices": (
            structured_context[
                "offices"
            ]
        ),

        "employment_type": (
            row.get(
                "employment_type"
            )
        ),

        "workplace_type": (
            row.get(
                "workplace_type"
            )
        ),

        "description": (
            row.get(
                "description_text"
            )
            or ""
        ),
    }


def build_content_hash(job) -> str:

    structured_context = (
        extract_structured_context(
            job.provider,
            job.raw,
        )
    )

    payload = {
        "title": job.title,

        "company": job.company,

        "location": job.location,

        "employment_type": (
            job.employment_type
        ),

        "workplace_type": (
            job.workplace_type
        ),

        "description": (
            job.description.text
        ),

        "structured_context": (
            structured_context
        ),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()