from app.core.config import settings
from app.core.search.base import SearchProvider
from app.core.search.duckduckgo import DuckDuckGoSearchProvider

PROVIDER_REGISTRY: dict[str, type[SearchProvider]] = {
    "duckduckgo": DuckDuckGoSearchProvider,
    # Tavily (or others) can be added here behind the same SearchProvider
    # interface without touching pipeline code — see docs/DECISIONS.md.
}


class UnknownSearchProviderError(Exception):
    pass


def get_search_provider() -> SearchProvider:
    provider_cls = PROVIDER_REGISTRY.get(settings.search_provider)
    if provider_cls is None:
        raise UnknownSearchProviderError(
            f"Unknown SEARCH_PROVIDER '{settings.search_provider}'. "
            f"Available: {', '.join(PROVIDER_REGISTRY)}"
        )
    return provider_cls()
