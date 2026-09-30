import pytest

from jobly.crawling.adapters.ashby import validate_ashby_response
from jobly.crawling.adapters.greenhouse import validate_greenhouse_response
from jobly.crawling.adapters.lever import validate_lever_response


@pytest.mark.parametrize(
    ("validator", "payload"),
    [
        (validate_greenhouse_response, []),
        (validate_greenhouse_response, {}),
        (validate_greenhouse_response, {"jobs": {}}),
        (validate_ashby_response, []),
        (validate_ashby_response, {}),
        (validate_ashby_response, {"jobs": None}),
        (validate_lever_response, {}),
    ],
)
def test_malformed_responses_are_rejected(validator, payload):
    with pytest.raises(ValueError):
        validator(payload)


def test_structurally_valid_empty_boards_are_allowed():
    assert validate_greenhouse_response({"jobs": []}) == []
    assert validate_ashby_response({"jobs": []}) == []
    assert validate_lever_response([]) == []
