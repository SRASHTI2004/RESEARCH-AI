"""The only place job sources touch the network — tests patch these
functions (see tests/conftest.py), so no test can accidentally hit a real
job board."""

from typing import Any

import requests

from app.core.config import settings


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.job_source_user_agent, "Accept": "application/json, */*"}


def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    res = requests.get(
        url,
        params=params,
        headers={**_headers(), **(headers or {})},
        timeout=settings.job_source_timeout_seconds,
    )
    res.raise_for_status()
    return res.json()


def post_form(url: str, data: dict[str, str], auth: tuple[str, str]) -> Any:
    """Form POST with HTTP basic auth (OAuth client-credentials token requests)."""
    res = requests.post(
        url, data=data, auth=auth, headers=_headers(), timeout=settings.job_source_timeout_seconds
    )
    res.raise_for_status()
    return res.json()


def get_text(url: str, params: dict[str, Any] | None = None) -> str:
    res = requests.get(url, params=params, headers=_headers(), timeout=settings.job_source_timeout_seconds)
    res.raise_for_status()
    return res.text
