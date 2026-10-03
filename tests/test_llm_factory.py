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
    monkeypatch.setattr(unconfigured, "is_configured", lambda: False)

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [unconfigured])

    with pytest.raises(LLMError, match="No LLM providers are configured"):
        invoke_llm("hello")


def test_empty_response_is_treated_as_failure_and_falls_back(monkeypatch):
    """A provider returning HTTP-200-but-blank content must not produce an empty report."""
    blank = _StubProvider("primary", lambda n: "   ")
    working = _StubProvider("secondary", lambda n: "real content")

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [blank, working])

    result = invoke_llm("hello")
    assert result == "real content"
    assert blank.calls == 2  # exhausted its retry budget on empty responses


def test_recovers_within_retry_budget_without_falling_back(monkeypatch):
    flaky = _StubProvider("primary", lambda n: ConnectionError("transient") if n < 2 else "ok")

    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [flaky])

    result = invoke_llm("hello")
    assert result == "ok"
    assert flaky.calls == 2


def test_retired_model_404_is_not_retried(monkeypatch):
    """A removed model fails identically every time — fall back immediately."""
    retired = _StubProvider(
        "primary", lambda n: RuntimeError("404 This model models/gemini-2.0-flash is no longer available.")
    )
    working = _StubProvider("secondary", lambda n: "fallback ok")
    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [retired, working])

    assert invoke_llm("hello") == "fallback ok"
    assert retired.calls == 1


def test_daily_quota_exhaustion_skips_provider_for_the_cooldown(monkeypatch):
    from app.core.llm import factory

    monkeypatch.setattr(factory, "_daily_quota_cooldown", {})
    exhausted = _StubProvider(
        "primary",
        lambda n: ProviderRateLimited("429 quota_id: GenerateRequestsPerDayPerProjectPerModel-FreeTier"),
    )
    working = _StubProvider("secondary", lambda n: "ok")
    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [exhausted, working])

    assert invoke_llm("one", stage="scoring") == "ok"
    calls_after_first = exhausted.calls
    assert invoke_llm("two", stage="scoring") == "ok"
    assert exhausted.calls == calls_after_first  # not even tried again
    # A different stage uses a different model/quota bucket, so it's still tried.
    invoke_llm("three", stage="writer")
    assert exhausted.calls > calls_after_first


def test_per_minute_rate_limit_does_not_trigger_cooldown(monkeypatch):
    from app.core.llm import factory

    monkeypatch.setattr(factory, "_daily_quota_cooldown", {})
    limited = _StubProvider("primary", lambda n: ProviderRateLimited("429 PerMinute quota"))
    working = _StubProvider("secondary", lambda n: "ok")
    monkeypatch.setattr("app.core.llm.factory._ordered_providers", lambda: [limited, working])

    invoke_llm("one")
    first = limited.calls
    invoke_llm("two")
    assert limited.calls > first
