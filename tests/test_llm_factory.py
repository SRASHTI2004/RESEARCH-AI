import pytest

from app.core.llm import LLMError
from app.core.llm.base import LLMProvider, ProviderRateLimited
from app.core.llm.factory import invoke_llm


class _StubProvider(LLMProvider):
    """Configurable stub used to drive the factory's retry/fallback logic directly."""

    def __init__(self, name: str, behavior):
        self.name = name
        self._behavior = behavior  # callable(call_count) -> str | Exception instance to raise
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    def invoke(self, prompt: str, *, temperature: float, stage: str) -> str:
        self.calls += 1
        result = self._behavior(self.calls)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    # Keep tests fast: patch the module-level settings used by the retry decorator.
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_max_retries", 2)


def test_falls_back_to_second_provider_after_first_exhausts_retries(monkeypatch):
    failing = _StubProvider("primary", lambda n: ConnectionError("down"))
    working = _StubProvider("secondary", lambda n: "secondary says hi")

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [failing, working])

    result = invoke_llm("hello")
    assert result == "secondary says hi"
    assert failing.calls == 2  # exhausted its retry budget
    assert working.calls == 1


def test_rate_limit_triggers_immediate_fallback_with_clear_message(monkeypatch):
    rate_limited = _StubProvider("primary", lambda n: ProviderRateLimited("429 quota exceeded"))

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [rate_limited])

    with pytest.raises(LLMError, match="rate limited"):
        invoke_llm("hello")


def test_no_configured_providers_raises_clear_error(monkeypatch):
    unconfigured = _StubProvider("primary", lambda n: "unused")
    unconfigured.is_configured = lambda: False

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [unconfigured])

    with pytest.raises(LLMError, match="No LLM providers are configured"):
        invoke_llm("hello")


def test_recovers_within_retry_budget_without_falling_back(monkeypatch):
    flaky = _StubProvider("primary", lambda n: ConnectionError("transient") if n < 2 else "ok")

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [flaky])

    result = invoke_llm("hello")
    assert result == "ok"
    assert flaky.calls == 2
