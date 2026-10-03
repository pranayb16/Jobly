from __future__ import annotations

from typing import Any

from jobly.enrichment.input_builder import extract_structured_context


def _raw_dict(raw: Any) -> dict:
    return raw if isinstance(raw, dict) else {}


def extract_deterministic_fields(job: dict[str, Any]) -> dict[str, Any]:
    """Extract trusted ATS fields without model inference."""
    raw = _raw_dict(job.get("raw_payload"))
    provider = str(job.get("provider") or "").lower()
    structured = extract_structured_context(provider, raw)

    employer_timestamps = {
        key: raw[key]
        for key in ("createdAt", "updatedAt", "publishedAt", "published_at")
        if raw.get(key) is not None
    }
    ats_identifiers = {
        "provider": provider,
        "external_job_id": job.get("external_job_id"),
    }
    salary = None
    for key in ("compensation", "salaryRange", "salary_range", "payRange"):
        if raw.get(key) is not None:
            salary = raw[key]
            break

    return {
        "departments": structured["departments"],
        "teams": structured["teams"],
        "offices": structured["offices"],
        "locations": structured["locations"],
        "primary_location": job.get("location"),
        "employment_type": job.get("employment_type"),
        "workplace_type": job.get("workplace_type"),
        "salary": salary,
        "employer_timestamps": employer_timestamps,
        "ats_identifiers": ats_identifiers,
    }
