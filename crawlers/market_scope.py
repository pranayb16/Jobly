import re
from dataclasses import dataclass
from typing import Any


US_STATE_CODES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}


US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia",
}


US_COUNTRY_VALUES = {
    "us",
    "usa",
    "u.s.",
    "u.s.a.",
    "united states",
    "united states of america",
}


@dataclass(frozen=True)
class USLocationDecision:
    eligible: bool
    reason: str


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def country_value_is_us(
    value: Any,
) -> bool:

    if value is None:
        return False


    if isinstance(
        value,
        dict,
    ):

        candidates = [
            value.get("code"),
            value.get("name"),
            value.get(
                "countryCode"
            ),
            value.get(
                "country_code"
            ),
        ]

        return any(
            country_value_is_us(
                candidate
            )
            for candidate
            in candidates
        )


    return (
        normalize_text(value)
        in US_COUNTRY_VALUES
    )


def text_has_us_country(
    value: Any,
) -> bool:

    text = normalize_text(
        value
    )

    if not text:
        return False


    patterns = [
        r"\bunited states\b",
        r"\bunited states of america\b",
        r"\bu\.s\.a\.",
        r"\bu\.s\.",
        r"(?:^|[\s,(/-])usa(?:$|[\s,)/-])",
        r"(?:^|[\s,(/-])us(?:$|[\s,)/-])",
    ]


    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None

        for pattern
        in patterns
    )


def text_has_us_state_name(
    value: Any,
) -> bool:

    text = normalize_text(
        value
    )

    if not text:
        return False


    for state in US_STATE_NAMES:

        if re.search(
            rf"\b{re.escape(state)}\b",
            text,
        ):
            return True


    return False


def text_has_us_state_code(
    value: Any,
) -> bool:

    if value is None:
        return False


    text = str(
        value
    ).strip()


    if not text:
        return False


    for code in US_STATE_CODES:

        patterns = [
            rf",\s*{code}\b",

            rf"\b{code}\s+\d{{5}}"
            rf"(?:-\d{{4}})?\b",

            rf"\b{code}\s*,\s*"
            rf"(?:US|USA)\b",

            rf"\b{code}\s*,\s*"
            rf"United States\b",
        ]


        for pattern in patterns:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                return True


    return False


def text_is_clearly_us(
    value: Any,
) -> bool:

    return (
        text_has_us_country(
            value
        )

        or text_has_us_state_name(
            value
        )

        or text_has_us_state_code(
            value
        )
    )


def extract_country_from_address(
    address: Any,
):

    if not isinstance(
        address,
        dict,
    ):
        return None


    postal = address.get(
        "postalAddress",
        address,
    )


    if not isinstance(
        postal,
        dict,
    ):
        return None


    return postal.get(
        "addressCountry"
    )


def ashby_has_us_country(
    raw: dict,
) -> bool:

    primary_country = (
        extract_country_from_address(
            raw.get(
                "address"
            )
        )
    )


    if country_value_is_us(
        primary_country
    ):
        return True


    secondary_locations = (
        raw.get(
            "secondaryLocations"
        )
        or []
    )


    for secondary in secondary_locations:

        if not isinstance(
            secondary,
            dict,
        ):
            continue


        country = (
            extract_country_from_address(
                secondary.get(
                    "address"
                )
            )
        )


        if country_value_is_us(
            country
        ):
            return True


    return False


def collect_location_strings(
    provider: str,
    raw: dict,
) -> list[str]:

    values = []


    if provider == "greenhouse":

        location = raw.get(
            "location"
        )

        if isinstance(
            location,
            dict,
        ):

            name = location.get(
                "name"
            )

            if name:
                values.append(
                    str(name)
                )


        for office in (
            raw.get(
                "offices"
            )
            or []
        ):

            if not isinstance(
                office,
                dict,
            ):
                continue


            name = office.get(
                "name"
            )

            location = office.get(
                "location"
            )


            if name:
                values.append(
                    str(name)
                )


            if location:
                values.append(
                    str(location)
                )


    elif provider == "ashby":

        location = raw.get(
            "location"
        )

        if location:
            values.append(
                str(location)
            )


        for secondary in (
            raw.get(
                "secondaryLocations"
            )
            or []
        ):

            if not isinstance(
                secondary,
                dict,
            ):
                continue


            location = (
                secondary.get(
                    "location"
                )
            )


            if location:
                values.append(
                    str(location)
                )


    elif provider == "lever":

        categories = (
            raw.get(
                "categories"
            )
            or {}
        )


        if isinstance(
            categories,
            dict,
        ):

            location = (
                categories.get(
                    "location"
                )
            )


            if location:
                values.append(
                    str(location)
                )


            all_locations = (
                categories.get(
                    "allLocations"
                )
            )


            if isinstance(
                all_locations,
                list,
            ):

                values.extend(
                    str(value)

                    for value
                    in all_locations

                    if value
                )


    return values


def classify_us_job(
    provider: str,
    location: str | None,
    raw: dict | None,
) -> USLocationDecision:

    provider = (
        provider
        or ""
    ).strip().lower()


    raw = (
        raw
        if isinstance(
            raw,
            dict,
        )
        else {}
    )


    # Ashby often gives us structured
    # country data. Prefer that.

    if (
        provider == "ashby"
        and ashby_has_us_country(
            raw
        )
    ):

        return USLocationDecision(
            eligible=True,
            reason=(
                "ashby_country_us"
            ),
        )


    # Primary normalized ATS location.

    if text_is_clearly_us(
        location
    ):

        return USLocationDecision(
            eligible=True,
            reason=(
                "primary_location_us"
            ),
        )


    # Search other structured ATS locations.

    location_strings = (
        collect_location_strings(
            provider,
            raw,
        )
    )


    for value in location_strings:

        if text_is_clearly_us(
            value
        ):

            return USLocationDecision(
                eligible=True,
                reason=(
                    "structured_location_us"
                ),
            )


    # Important:
    #
    # "Remote" alone does NOT prove
    # that a role is available in the U.S.

    return USLocationDecision(
        eligible=False,
        reason=(
            "no_clear_us_evidence"
        ),
    )