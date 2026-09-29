from crawlers.models import Job,JobDescription


def normalize_lever(raw: dict, company: str) -> Job:
    categories = raw.get("categories") or {}

    return Job(
        external_job_id=raw["id"],
        provider="lever",

        company=company,
        title=raw["text"],

        location=categories.get("location"),
        employment_type=categories.get("commitment"),
        workplace_type=raw.get("workplaceType"),

        posted_at=None,
        posted_at_source=None,

        description=JobDescription(
            html=raw.get("description"),
            text=raw.get("descriptionPlain"),
        ),

        job_url=raw.get("hostedUrl"),
        apply_url=raw.get("applyUrl"),

        raw=raw,
    )