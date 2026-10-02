import pytest
from fastapi.testclient import TestClient

from app.main import app

FAKE_SOURCES = [
    {
        "index": 1,
        "title": "Acme Corp — Official Site",
        "url": "https://acme.example.com",
        "snippet": "Acme Corp builds widgets.",
        "content": "Acme Corp builds widgets and was founded in 2001.",
    },
    {
        "index": 2,
        "title": "Acme Corp raises Series B",
        "url": "https://news.example.com/acme-series-b",
        "snippet": "Acme Corp raised a Series B round.",
        "content": "Acme Corp raised a $50M Series B round in 2024.",
    },
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Prevent any real LLM provider calls during tests.

    Agents call through `app.core.llm` as a module (`llm.invoke_llm(...)`)
    rather than importing the function directly, so patching the attribute
    here affects every call site.
    """

    def _fake_invoke(prompt: str, *, temperature: float = 0.3, stage: str = "default") -> str:
        return f"MOCKED[{stage}] response for prompt starting with: {prompt[:30]!r}"

    monkeypatch.setattr("app.core.llm.invoke_llm", _fake_invoke)


@pytest.fixture(autouse=True)
def mock_search(monkeypatch):
    """Prevent any real web search / page-fetch network calls during tests."""

    def _fake_gather_sources(company: str, **kwargs) -> list[dict]:
        return FAKE_SOURCES

    monkeypatch.setattr("app.pipeline.agents.researcher.gather_sources", _fake_gather_sources)
