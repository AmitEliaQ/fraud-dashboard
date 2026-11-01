import pytest
import requests

import api_client
from api_client import BackendError


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self._body = body

    def json(self):
        return self._body


@pytest.fixture
def backend(monkeypatch):
    """Replay queued outcomes for successive requests, without sleeping."""
    calls = []
    outcomes = []

    def fake_request(method, url, **kwargs):
        calls.append(url)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(api_client.requests, "request", fake_request)
    monkeypatch.setattr(api_client.time, "sleep", lambda _: None)
    return outcomes, calls


def test_retries_until_sleeping_backend_wakes(backend):
    outcomes, calls = backend
    outcomes += [requests.ConnectionError(), FakeResponse(503), FakeResponse(200, {"status": "ok"})]
    assert api_client.get_health() == {"status": "ok"}
    assert len(calls) == 3


def test_gives_up_after_all_retries(backend):
    outcomes, calls = backend
    outcomes += [requests.Timeout() for _ in range(4)]
    with pytest.raises(BackendError, match="Timeout"):
        api_client.get_health()
    assert len(calls) == 4


def test_client_error_is_not_retried(backend):
    outcomes, calls = backend
    outcomes.append(FakeResponse(422))
    with pytest.raises(BackendError, match="422"):
        api_client.get_transactions({})
    assert len(calls) == 1


def test_environment_mismatch_detected():
    assert api_client.environment_mismatch("prod", "dev") is not None
    assert api_client.environment_mismatch("dev", "dev") is None
