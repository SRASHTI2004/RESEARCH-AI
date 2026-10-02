from abc import ABC, abstractmethod


class ProviderRateLimited(Exception):
    """Raised by a provider implementation when the failure looks like a rate limit."""


class LLMProvider(ABC):
    name: str

    def is_configured(self) -> bool:
        """Whether this provider has what it needs (e.g. an API key) to be tried."""
        return True

    @abstractmethod
    def invoke(self, prompt: str, *, temperature: float, stage: str) -> str:
        """Return the model's text response. Raise on failure (including rate limits)."""
