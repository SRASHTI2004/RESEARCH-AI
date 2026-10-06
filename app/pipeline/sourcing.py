"""Gathers numbered, citable sources for a company before any LLM call happens.

This is what makes the Researcher stage retrieval-grounded instead of just
asking the LLM to recall facts from training data — see docs/DECISIONS.md
for why that matters and where it still falls short.
"""

import logging

from app.core.search import get_search_provider
from app.core.search.fetch import fetch_page_text

logger = logging.getLogger(__name__)

QUERY_TEMPLATES = [
    "{company} company overview",
    "{company} latest news",
    "{company} engineering technology stack",
    "{company} interview questions software engineer",
]


def gather_sources(
    company: str,
    *,
    results_per_query: int,
    fetch_timeout: float,
    max_content_chars: int,
) -> list[dict]:
    """Search each query template, fetch page content, dedupe by URL.

    Returns a list of {index, title, url, snippet, content} dicts, numbered
    starting at 1 — that number is the citation key used throughout the
    pipeline and persisted alongside the report.
    """
    provider = get_search_provider()
    seen_urls: set[str] = set()
    sources: list[dict] = []

    for template in QUERY_TEMPLATES:
        query = template.format(company=company)
        try:
            results = provider.search(query, max_results=results_per_query)
        except Exception as exc:
            logger.warning("Search failed for query %r: %s", query, exc)
            continue

        for result in results:
            if not result.url or result.url in seen_urls:
                continue
            seen_urls.add(result.url)

            content = fetch_page_text(result.url, timeout=fetch_timeout, max_chars=max_content_chars)

            sources.append(
                {
                    "index": len(sources) + 1,
                    "title": result.title or result.url,
                    "url": result.url,
                    "snippet": result.snippet,
                    "content": content or result.snippet,
                }
            )

    return sources


def format_sources_for_prompt(sources: list[dict]) -> str:
    return "\n\n".join(f"[{s['index']}] {s['title']} ({s['url']})\n{s['content']}" for s in sources)


def format_source_list(sources: list[dict]) -> str:
    """Short title/url-only listing — used in prompts that don't need full content."""
    return "\n".join(f"[{s['index']}] {s['title']} — {s['url']}" for s in sources)
