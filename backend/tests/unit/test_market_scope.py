from jobly.market.us_scope import classify_us_job


def test_explicit_us_location_is_eligible():
    decision = classify_us_job("greenhouse", "Chicago, IL", {})
    assert decision.eligible is True


def test_remote_alone_is_not_us_evidence():
    decision = classify_us_job("lever", "Remote", {"categories": {"location": "Remote"}})
    assert decision.eligible is False
    assert decision.scope == "unknown"
    assert decision.reason == "no_clear_us_evidence"


def test_ashby_structured_us_country_is_eligible():
    raw = {"address": {"postalAddress": {"addressCountry": "US"}}}
    decision = classify_us_job("ashby", "Remote", raw)
    assert decision.eligible is True
    assert decision.reason == "ashby_country_us"


def test_georgia_country_is_not_treated_as_us_state():
    assert classify_us_job("greenhouse", "Tbilisi, Georgia", {}).scope == "non_us"
    assert classify_us_job(
        "ashby",
        "Remote",
        {"address": {"postalAddress": {"addressCountry": "GE"}}},
    ).scope == "non_us"
    assert classify_us_job("greenhouse", "Atlanta, GA", {}).scope == "us"
    assert classify_us_job("greenhouse", "Georgia, USA", {}).scope == "us"


def test_description_evidence_resolves_remote_scope():
    assert classify_us_job(
        "lever",
        "Remote",
        {},
        "This role is remote within the United States.",
    ).scope == "us"
    assert classify_us_job(
        "lever",
        None,
        {},
        "This role is available only in Canada.",
    ).scope == "non_us"
    assert classify_us_job(
        "lever",
        "Remote",
        {},
        "Work remotely from anywhere worldwide.",
    ).scope == "unknown"
