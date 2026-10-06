import pytest

from jobly.enrichment.input_builder import build_content_hash, compact_description
from jobly.jobs.models import Job, JobDescription


def make_job(description: str = "Build systems") -> Job:
    return Job(
        external_job_id="1",
        provider="lever",
        company="Example",
        title="Engineer",
        location="Austin, TX",
        description=JobDescription(text=description),
        raw={"categories": {"department": "Engineering"}},
    )


def test_content_hash_is_stable():
    assert build_content_hash(make_job()) == build_content_hash(make_job())


def test_content_hash_changes_with_content():
    assert build_content_hash(make_job()) != build_content_hash(make_job("Different work"))


@pytest.mark.parametrize(
    "heading",
    ["Who you are", "What you bring", "Minimum qualifications"],
)
def test_compaction_preserves_requirements_after_benefits(heading):
    description = "\n".join(
        [
            "About the role",
            "Build reliable systems for customers.",
            "Benefits",
            "Health and dental coverage.",
            heading,
            "Minimum 7+ years of professional experience.",
        ]
    )

    assert "7+ years" in compact_description(description)
