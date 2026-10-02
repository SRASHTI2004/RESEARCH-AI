from app.core.search.base import SearchResult
from app.pipeline.sourcing import format_source_list, format_sources_for_prompt, gather_sources


class _StubSearchProvider:
    def __init__(self, results_by_query: dict[str, list[SearchResult]]):
        self._results_by_query = results_by_query

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        for key, results in self._results_by_query.items():
            if key in query:
                return results[:max_results]
        return []


def test_gather_sources_dedupes_by_url(monkeypatch):
    duplicate = SearchResult(title="Acme Home", url="https://acme.example.com", snippet="s")
    provider = _StubSearchProvider(
        {
            "overview": [duplicate],
            "news": [duplicate],  # same URL turns up under a different query
            "technology": [SearchResult(title="Acme Eng Blog", url="https://acme.example.com/blog", snippet="s2")],
            "interview": [],
        }
    )

    monkeypatch.setattr("app.pipeline.sourcing.get_search_provider", lambda: provider)
    monkeypatch.setattr("app.pipeline.sourcing.fetch_page_text", lambda url, **kw: f"content for {url}")

    sources = gather_sources("Acme", results_per_query=5, fetch_timeout=5.0, max_content_chars=100)

    urls = [s["url"] for s in sources]
    assert urls == ["https://acme.example.com", "https://acme.example.com/blog"]
    assert sources[0]["index"] == 1
    assert sources[1]["index"] == 2


def test_gather_sources_falls_back_to_snippet_when_fetch_fails(monkeypatch):
    provider = _StubSearchProvider(
        {"overview": [SearchResult(title="Acme Home", url="https://acme.example.com", snippet="fallback text")]}
    )
    monkeypatch.setattr("app.pipeline.sourcing.get_search_provider", lambda: provider)
    monkeypatch.setattr("app.pipeline.sourcing.fetch_page_text", lambda url, **kw: None)

    sources = gather_sources("Acme", results_per_query=5, fetch_timeout=5.0, max_content_chars=100)

    assert sources[0]["content"] == "fallback text"


def test_gather_sources_skips_query_when_search_raises(monkeypatch):
    class _Boom:
        def search(self, query, *, max_results):
            raise RuntimeError("search provider down")

    monkeypatch.setattr("app.pipeline.sourcing.get_search_provider", lambda: _Boom())

    sources = gather_sources("Acme", results_per_query=5, fetch_timeout=5.0, max_content_chars=100)

    assert sources == []


def test_format_helpers_include_citation_numbers():
    sources = [{"index": 1, "title": "T1", "url": "https://u1", "snippet": "s1", "content": "c1"}]

    assert "[1] T1 (https://u1)" in format_sources_for_prompt(sources)
    assert "[1] T1 — https://u1" in format_source_list(sources)
