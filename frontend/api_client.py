"""HTTP client for the backend. Free Render services sleep when idle, so the
first request after a quiet period can take about a minute."""
import os
import time

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
APP_ENV = os.environ.get("APP_ENV", "local")

TIMEOUT_SECONDS = 90
RETRY_DELAYS_SECONDS = (5, 10, 20)
# Render's proxy can answer with these while a sleeping service starts.
RETRYABLE_STATUS = {502, 503, 504}


class BackendError(Exception):
    """The backend could not be reached or rejected the request."""


def _request(method: str, path: str, **kwargs) -> dict:
    url = f"{BACKEND_URL}{path}"
    failure = "no attempt made"
    for delay in (*RETRY_DELAYS_SECONDS, None):
        try:
            response = requests.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            failure = type(exc).__name__
        else:
            if response.status_code not in RETRYABLE_STATUS:
                if not response.ok:
                    raise BackendError(f"{method} {url} returned HTTP {response.status_code}")
                return response.json()
            failure = f"HTTP {response.status_code}"
        if delay is not None:
            time.sleep(delay)
    raise BackendError(f"{method} {url} failed: {failure}")


def environment_mismatch(backend_env: str, frontend_env: str = APP_ENV) -> str | None:
    """Describe a dev/prod wiring mistake, or return None when both sides agree."""
    if backend_env == frontend_env:
        return None
    return f"frontend is '{frontend_env}' but backend {BACKEND_URL} is '{backend_env}'"


def get_health() -> dict:
    return _request("GET", "/health")


def get_meta() -> dict:
    return _request("GET", "/meta")


def get_transactions(filters: dict) -> dict:
    return _request("POST", "/transactions", json=filters)


def get_predictive_features(filters: dict) -> dict:
    return _request("POST", "/predictive-features", json=filters)
