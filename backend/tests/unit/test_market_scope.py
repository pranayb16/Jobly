from jobly.market.us_scope import classify_us_job


def test_explicit_us_location_is_eligible():
    decision = classify_us_job("greenhouse", "Chicago, IL", {})
    assert decision.eligible is True


def test_remote_alone_is_not_us_evidence():
    decision = classify_us_job("lever", "Remote", {"categories": {"location": "Remote"}})
    assert decision.eligible is False
    assert decision.reason == "no_clear_us_evidence"


def test_ashby_structured_us_country_is_eligible():
    raw = {"address": {"postalAddress": {"addressCountry": "US"}}}
    decision = classify_us_job("ashby", "Remote", raw)
    assert decision.eligible is True
    assert decision.reason == "ashby_country_us"
