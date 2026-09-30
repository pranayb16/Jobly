from jobly.jobs.models import (
    Job,
    JobDescription,
)


def normalize_ashby(
    raw: dict,
    company: str,
) -> Job:

    return Job(
        external_job_id=str(
            raw["id"]
        ),

        provider="ashby",

        company=company,

        title=raw["title"],

        location=raw.get(
            "location"
        ),

        employment_type=raw.get(
            "employmentType"
        ),

        workplace_type=raw.get(
            "workplaceType"
        ),

        posted_at=raw.get(
            "publishedAt"
        ),

        posted_at_source=(
            "ashby.publishedAt"
        ),

        description=JobDescription(
            html=raw.get(
                "descriptionHtml"
            ),

            text=raw.get(
                "descriptionPlain"
            ),
        ),

        job_url=raw.get(
            "jobUrl"
        ),

        apply_url=raw.get(
            "applyUrl"
        ),

        raw=raw,
    )
