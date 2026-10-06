from jobly.config import get_settings
from jobly.enrichment.classifier import _request_openrouter, _usage_from_response


class Response:
    ok = True


def test_paid_provider_configuration_and_output_cap_are_honored(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MAX_OUTPUT_TOKENS", "1234")
    monkeypatch.setenv("OPENROUTER_PAID_PROVIDERS", "provider-a,provider-b")
    get_settings.cache_clear()
    captured = {}

    def post(_url, **kwargs):
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("jobly.enrichment.classifier.requests.post", post)
    settings = get_settings()
    _request_openrouter(
        model=settings.openrouter_paid_model,
        messages=[],
        response_schema={"type": "object"},
        providers=settings.openrouter_paid_providers,
    )

    assert captured["json"]["provider"]["order"] == ["provider-a", "provider-b"]
    assert captured["json"]["max_tokens"] == 1234
    get_settings.cache_clear()


def test_malformed_usage_does_not_reject_valid_classification():
    usage = _usage_from_response(
        {
            "id": "request-1",
            "model": "model-1",
            "provider": "provider-1",
            "usage": {
                "prompt_tokens": "not-a-number",
                "completion_tokens": None,
                "total_tokens": [],
            },
        },
        fallback_model="fallback",
    )
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0
    assert usage.provider == "provider-1"
