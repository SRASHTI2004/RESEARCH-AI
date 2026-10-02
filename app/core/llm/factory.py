import logging

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.llm.base import LLMProvider, ProviderRateLimited
from app.core.llm.providers import PROVIDER_REGISTRY

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when every configured provider has failed (or none are configured)."""


class EmptyLLMResponseError(Exception):
    """Raised when a provider returns HTTP 200 but a blank/whitespace-only response.

    Seen in practice with Groq's reasoning models (e.g. openai/gpt-oss-120b)
    on long prompts — the call succeeds but content comes back empty. This
    makes that count as a retryable failure instead of silently producing
    an empty report.
    """


def _ordered_providers() -> list[LLMProvider]:
    names = [p.strip() for p in settings.llm_provider_order.split(",") if p.strip()]
    providers = []
    for name in names:
        provider_cls = PROVIDER_REGISTRY.get(name)
        if provider_cls is None:
            logger.warning("Unknown LLM provider '%s' in LLM_PROVIDER_ORDER, skipping", name)
            continue
        providers.append(provider_cls())
    return providers


def _call_with_retries(provider: LLMProvider, prompt: str, temperature: float, stage: str) -> str:
    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _attempt() -> str:
        content = provider.invoke(prompt, temperature=temperature, stage=stage)
        if not content or not content.strip():
            raise EmptyLLMResponseError(f"Provider '{provider.name}' returned an empty response")
        return content

    return _attempt()


def invoke_llm(prompt: str, *, temperature: float = 0.3, stage: str = "default") -> str:
    """Call the first configured, healthy provider in LLM_PROVIDER_ORDER.

    Each provider gets its own retry budget with exponential backoff before
    we fall back to the next one. Rate-limit responses are detected and
    logged distinctly so it's clear from logs *why* a fallback happened.
    Raises LLMError with a human-readable summary once every provider has
    failed — callers never see raw provider exceptions.
    """
    errors: list[str] = []
    attempted = False

    for provider in _ordered_providers():
        if not provider.is_configured():
            logger.debug("Skipping LLM provider '%s': not configured", provider.name)
            continue

        attempted = True
        try:
            return _call_with_retries(provider, prompt, temperature, stage)
        except ProviderRateLimited as exc:
            logger.warning("LLM provider '%s' rate-limited, falling back: %s", provider.name, exc)
            errors.append(f"{provider.name}: rate limited")
        except Exception as exc:
            logger.warning("LLM provider '%s' failed after retries, falling back: %s", provider.name, exc)
            errors.append(f"{provider.name}: {exc}")

    if not attempted:
        raise LLMError(
            "No LLM providers are configured. Set GEMINI_API_KEY and/or GROQ_API_KEY "
            "in .env (see .env.example)."
        )

    raise LLMError("All configured LLM providers failed: " + "; ".join(errors))
