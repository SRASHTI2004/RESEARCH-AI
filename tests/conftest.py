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


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Rate limits are keyed by client IP, and TestClient always presents
    the same fake address — without resetting, tests exhaust auth
    endpoints' limits after a handful of register/login calls and every
    test after that starts seeing 429s instead of real responses."""
    from app.core.rate_limit import limiter

    limiter.reset()


@pytest.fixture(autouse=True)
def _use_test_db_for_worker(monkeypatch):
    """The Celery task opens its own DB session (it doesn't go through
    FastAPI's dependency injection), so overriding `get_db` alone isn't
    enough — without this, the eager-mode task would write to the real
    app.db file instead of this test's in-memory DB, and every
    research-job test would see status stuck at "pending" forever."""
    monkeypatch.setattr("app.worker.tasks.SessionLocal", _TestingSessionLocal)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    """Direct session onto the same in-memory test DB — for tests that
    exercise repositories/worker tasks without going through the API."""
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@pytest.fixture(autouse=True)
def block_job_source_network(monkeypatch):
    """Job sources only reach the network through app.core.jobsources.http —
    fail loudly if a test forgets to stub it, instead of hitting real boards."""

    def _blocked(url, params=None):
        raise AssertionError(f"Unmocked job-source HTTP call in a test: {url}")

    monkeypatch.setattr("app.core.jobsources.http.get_json", _blocked)
    monkeypatch.setattr("app.core.jobsources.http.get_text", _blocked)


@pytest.fixture(autouse=True)
def block_notifications(monkeypatch):
    """No test may reach Telegram or an SMTP server; tests that exercise the
    channels install their own fakes on top of this."""

    def _no_post(*args, **kwargs):
        raise AssertionError("Unmocked Telegram HTTP call in a test")

    def _no_smtp(*args, **kwargs):
        raise AssertionError("Unmocked SMTP connection in a test")

    # Start every test from "nothing configured", whatever the developer's
    # real .env contains (tokens there must never influence or leak into tests).
    from app.core.config import settings

    for name in (
        "telegram_bot_token",
        "telegram_chat_id",
        "smtp_username",
        "smtp_password",
        "digest_email_to",
    ):
        monkeypatch.setattr(settings, name, "")
    monkeypatch.setattr(settings, "digest_telegram_enabled", False)
    monkeypatch.setattr(settings, "digest_email_enabled", False)
    monkeypatch.setattr(settings, "app_base_url", "http://localhost:5173")

    monkeypatch.setattr("app.core.notify.requests.post", _no_post)
    monkeypatch.setattr("app.core.notify.smtplib.SMTP", _no_smtp)
    monkeypatch.setattr("app.services.scoring_service._sleep", lambda seconds: None)


@pytest.fixture(autouse=True)
def use_example_personal_files(monkeypatch):
    """Tests never read the developer's real profile or master resume."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "profile_path", "config/profile.example.yaml")
    monkeypatch.setattr(settings, "master_resume_path", "data/master_resume.example.yaml")


@pytest.fixture
def testing_session_factory():
    return _TestingSessionLocal


@pytest.fixture
def profile():
    from app.core.profile import LocationPrefs, Profile

    return Profile(
        name="Test User",
        email="test@example.com",
        college="Test Institute of Technology",
        primary_skills=["Python", "React", "TypeScript", "FastAPI"],
        secondary_skills=["SQL", "Docker"],
        locations=LocationPrefs(preferred_cities=["Pune"]),
    )


def _register_and_login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_admin(email: str) -> None:
    db = _TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
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
