"""One class per LLM provider, behind the shared LLMProvider interface.

SDK imports are done lazily inside invoke() so that, say, a broken/absent
Ollama install can't break Gemini or Groq usage unless Ollama is actually
selected in LLM_PROVIDER_ORDER.
"""

import logging

from app.core.config import settings
from app.core.llm.base import LLMProvider, ProviderRateLimited

logger = logging.getLogger(__name__)

_RATE_LIMIT_MARKERS = ("rate limit", "rate_limit", "quota", "429", "resourceexhausted", "resource_exhausted")


def _looks_like_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def _model_for_stage(default_model: str, writer_model: str, stage: str, scoring_model: str = "") -> str:
    if stage == "writer":
        return writer_model
    if stage == "scoring" and scoring_model:
        return scoring_model
    return default_model


def _as_text(content: str | list[str | dict]) -> str:
    """LangChain's AIMessage.content is typed str | list[...] to allow for
    multimodal responses; our text-only chat models always return a plain
    str at runtime, but mypy doesn't know that — so we assert it instead of
    silencing the check."""
    if not isinstance(content, str):
        raise TypeError(f"Expected a plain text response, got {type(content).__name__}")
    return content


class GeminiProvider(LLMProvider):
    name = "gemini"

    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    def invoke(self, prompt: str, *, temperature: float, stage: str) -> str:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = _model_for_stage(
            settings.gemini_model, settings.gemini_writer_model, stage, settings.gemini_scoring_model
        )
        client = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            timeout=settings.llm_timeout_seconds,
        )
        try:
            return _as_text(client.invoke(prompt).content)
        except Exception as exc:
            if _looks_like_rate_limit(exc):
                raise ProviderRateLimited(str(exc)) from exc
            raise


class GroqProvider(LLMProvider):
    name = "groq"

    def is_configured(self) -> bool:
        return bool(settings.groq_api_key)

    def invoke(self, prompt: str, *, temperature: float, stage: str) -> str:
        from langchain_groq import ChatGroq

        model = _model_for_stage(
            settings.groq_model, settings.groq_writer_model, stage, settings.groq_scoring_model
        )
        client = ChatGroq(
            model=model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        try:
            return _as_text(client.invoke(prompt).content)
        except Exception as exc:
            if _looks_like_rate_limit(exc):
                raise ProviderRateLimited(str(exc)) from exc
            raise


class OllamaProvider(LLMProvider):
    """Local-only provider — not in the default fallback chain. Needs `ollama serve`."""

    name = "ollama"

    def invoke(self, prompt: str, *, temperature: float, stage: str) -> str:
        from langchain_ollama import ChatOllama

        client = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
        return _as_text(client.invoke(prompt).content)


PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
}
