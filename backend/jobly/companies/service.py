from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_company_name(name: str) -> str:
    """Normalize exact identity only; this deliberately does no fuzzy matching."""
    normalized = unicodedata.normalize("NFKC", name)
    return " ".join(normalized.casefold().split())


def company_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if slug:
        return slug
    return f"company-{hashlib.sha256(name.encode()).hexdigest()[:10]}"


def collision_safe_slug(name: str, normalized_name: str) -> str:
    return f"{company_slug(name)}-{hashlib.sha256(normalized_name.encode()).hexdigest()[:8]}"
