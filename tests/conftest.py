import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.main import app
from app.models import Base, User

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

DEFAULT_PASSWORD = "password123"

# In-memory SQLite shared across connections (StaticPool) so the same DB is
# visible both to the test and to the app's request-scoped sessions.
_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
_TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


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


def _register_and_login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_admin(email: str) -> None:
    db = _TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.role = "admin"
        db.commit()
    finally:
        db.close()


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    """Headers for a freshly registered, logged-in regular user."""
    return _register_and_login(client, "user@example.com")


@pytest.fixture
def make_user_headers(client: TestClient):
    """Factory for registering+logging in additional users, e.g. a second
    distinct user to test that one user can't see another's jobs."""

    def _make(email: str, *, admin: bool = False) -> dict:
        headers = _register_and_login(client, email)
        if admin:
            _make_admin(email)
            headers = _register_and_login(client, email)  # re-login so the token's role claim is current
        return headers

    return _make
