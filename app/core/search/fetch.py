import logging

import requests
import trafilatura

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ResearchAI/1.0; +company-research-brief)"}


def fetch_page_text(url: str, *, timeout: float, max_chars: int) -> str | None:
    """Fetch a URL and extract its main article text.

    Returns None (never raises) on any failure — a page that can't be
    fetched just falls back to its search-result snippet instead of
    aborting the whole research run.
    """
    try:
        response = requests.get(url, headers=_HEADERS, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None

    try:
        extracted = trafilatura.extract(response.text)
    except Exception as exc:
        logger.warning("Failed to extract content from %s: %s", url, exc)
        return None

    if not extracted:
        return None

    return extracted[:max_chars]
