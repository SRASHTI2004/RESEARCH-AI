from app.core.search.base import SearchProvider, SearchResult


class DuckDuckGoSearchProvider(SearchProvider):
    """Free, no-API-key web search via the `ddgs` package."""

    name = "duckduckgo"

    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        from ddgs import DDGS

        with DDGS() as client:
            raw_results = list(client.text(query, max_results=max_results))

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
            )
            for item in raw_results
            if item.get("href")
        ]
