import hashlib
import json
import re
from typing import Any


# ============================================================
# DESCRIPTION COMPACTION
# ============================================================

BOILERPLATE_HEADINGS = (
    "about us",
    "about the company",
    "our company",
    "our culture",
    "culture",
    "what we offer",
    "benefits",
    "our benefits",
    "perks",
    "perks and benefits",
    "health and wellbeing",
    "growth and future",
    "community",
    "equal opportunity",
    "equal employment opportunity",
    "diversity and inclusion",
    "diversity, equity and inclusion",
    "accommodation",
    "accommodations",
    "candidate privacy",
    "privacy notice",
    "our approach to remote work",
    "how we work with ai",
)


RELEVANT_HEADINGS = (
    "about the role",
    "about the job",
    "the role",
    "role overview",
    "position overview",
    "what you'll do",
    "what you’ll do",
    "what you will do",
    "what you will build",
    "responsibilities",
    "your responsibilities",
    "what we're looking for",
    "what we’re looking for",
    "what we are looking for",
    "requirements",
    "minimum requirements",
    "minimum qualifications",
    "qualifications",
    "preferred qualifications",
    "preferred requirements",
    "skills",
    "experience",
    "education",
    "compensation",
    "salary",
    "pay range",
    "location",
    "work authorization",
    "visa sponsorship",
    "security clearance",
)


LEGAL_PATTERNS = (
    "equal opportunity employer",
    "equal employment opportunity",
    "do not discriminate on the basis",
    "reasonable accommodation",
    "accommodation is available",
    "candidate privacy notice",
    "privacy policy",
    "background check may consist",
    "successful applicants will be required to complete a background check",
    "artificial intelligence (ai) and machine learning (ml) technologies",
    "assist in the initial screening of employment applications",
)


def _normalize_heading(
    value: str,
) -> str:
    value = value.strip().lower()

    value = re.sub(
        r"[:\-–—]+$",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _looks_like_heading(
    value: str,
) -> bool:
    value = value.strip()

    if not value:
        return False

    if len(value) > 100:
        return False

    if value.startswith(
        (
            "-",
            "•",
            "*",
        )
    ):
        return False

    # Long normal sentences are unlikely to be headings.
    if (
        value.endswith(".")
        and len(value.split()) > 8
    ):
        return False

    return True


def _is_boilerplate_heading(
    value: str,
) -> bool:
    normalized = _normalize_heading(
        value
    )

    if normalized.startswith("about "):
        # Keep role-specific "about the role/job",
        # but drop company biography sections.
        if normalized in {
            "about the role",
            "about the job",
            "about this role",
        }:
            return False

        return True

    return normalized in BOILERPLATE_HEADINGS


def _is_relevant_heading(
    value: str,
) -> bool:
    normalized = _normalize_heading(
        value
    )

    return normalized in RELEVANT_HEADINGS


def _is_legal_boilerplate(
    value: str,
) -> bool:
    lowered = value.lower()

    return any(
        pattern in lowered
        for pattern in LEGAL_PATTERNS
    )


def compact_description(
    description: str,
) -> str:
    """
    Remove obvious company/legal/benefits boilerplate before
    sending a job description to the AI model.

    Important:
    - This affects AI input only.
    - build_content_hash() still uses the complete original JD.
    """

    if not description:
        return ""

    # Normalize newlines and excessive spaces while preserving
    # sections/bullets.
    description = description.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    lines = []

    for raw_line in description.split("\n"):
        line = re.sub(
            r"[ \t]+",
            " ",
            raw_line,
        ).strip()

        if line:
            lines.append(line)

    if not lines:
        return ""

    kept: list[str] = []

    skipping_boilerplate = False

    for line in lines:
        heading_like = _looks_like_heading(
            line
        )

        if (
            heading_like
            and _is_boilerplate_heading(
                line
            )
        ):
            skipping_boilerplate = True
            continue

        if (
            heading_like
            and _is_relevant_heading(
                line
            )
        ):
            skipping_boilerplate = False
            kept.append(line)
            continue

        if skipping_boilerplate:
            continue

        if _is_legal_boilerplate(
            line
        ):
            continue

        kept.append(line)

    compacted = "\n".join(
        kept
    ).strip()

    # Safety fallback:
    # if a strange JD structure causes us to remove too much,
    # send the original description instead.
    if len(compacted) < 500:
        compacted = "\n".join(
            lines
        )

    return compacted


# ============================================================
# GENERAL HELPERS
# ============================================================

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


# ============================================================
# GREENHOUSE
# ============================================================

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
        if not isinstance(
            office,
            dict,
        ):
            continue

        office_name = office.get(
            "name"
        )

        office_location = office.get(
            "location"
        )

        if office_name:
            offices.append(
                office_name
            )

        if office_location:
            locations.append(
                office_location
            )

    return {
        "departments":
            unique_strings(
                departments
            ),

        "teams":
            [],

        "locations":
            unique_strings(
                locations
            ),

        "offices":
            unique_strings(
                offices
            ),
    }


# ============================================================
# ASHBY
# ============================================================

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
        locations.append(
            address
        )

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
            locations.append(
                location
            )

        address = format_postal_address(
            secondary.get("address")
        )

        if address:
            locations.append(
                address
            )

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
        "departments":
            unique_strings(
                departments
            ),

        "teams":
            unique_strings(
                teams
            ),

        "locations":
            unique_strings(
                locations
            ),

        "offices":
            [],
    }


# ============================================================
# LEVER
# ============================================================

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

    if categories.get(
        "location"
    ):
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

    if categories.get(
        "department"
    ):
        departments.append(
            categories["department"]
        )

    teams = []

    if categories.get(
        "team"
    ):
        teams.append(
            categories["team"]
        )

    return {
        "departments":
            unique_strings(
                departments
            ),

        "teams":
            unique_strings(
                teams
            ),

        "locations":
            unique_strings(
                locations
            ),

        "offices":
            [],
    }


# ============================================================
# STRUCTURED ATS CONTEXT
# ============================================================

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


# ============================================================
# AI PAYLOAD
# ============================================================

def build_classifier_payload(
    row: dict[str, Any],
) -> dict:
    """
    Build the smallest useful semantic payload for Gemini.

    Structured ATS facts are added separately by worker.py as
    trusted_structured_context, so they are intentionally not
    duplicated here.
    """

    description = (
        row.get(
            "description_text"
        )
        or ""
    )

    return {
        "original_title":
            row["title"],

        "company":
            row.get(
                "company"
            ),

        "description":
            compact_description(
                description
            ),
    }


# ============================================================
# CONTENT HASH
# ============================================================

def build_content_hash(
    job,
) -> str:
    """
    Content hash intentionally continues to use the complete
    original job description.

    AI input compaction must never prevent Jobly from noticing
    that the underlying posting changed.
    """

    structured_context = (
        extract_structured_context(
            job.provider,
            job.raw,
        )
    )

    payload = {
        "title":
            job.title,

        "company":
            job.company,

        "location":
            job.location,

        "employment_type":
            job.employment_type,

        "workplace_type":
            job.workplace_type,

        "description":
            job.description.text,

        "structured_context":
            structured_context,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()