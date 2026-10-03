from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    id: int
    name: str
    normalized_name: str
    slug: str
    website_domain: str | None = None
