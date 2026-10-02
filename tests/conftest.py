import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Prevent any real network/LLM calls during tests.

    Agents call through `app.core.llm` as a module (`llm.invoke_llm(...)`)
    rather than importing the function directly, so patching the attribute
    here affects every call site.
    """

    def _fake_invoke(prompt: str, *, temperature: float = 0.3, stage: str = "default") -> str:
        return f"MOCKED[{stage}] response for prompt starting with: {prompt[:30]!r}"

    monkeypatch.setattr("app.core.llm.invoke_llm", _fake_invoke)
