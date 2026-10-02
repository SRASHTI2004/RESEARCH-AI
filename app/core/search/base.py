from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        """Return up to max_results results. Raise on failure — callers decide how to handle it."""
