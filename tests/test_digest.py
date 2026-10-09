import logging
import smtplib
from datetime import UTC, datetime, timedelta

import pytest
import requests

from app.core import notify
from app.models.job import Job
from app.services import digest_service
from tests.factories import make_job

TOKEN = "123456:SECRET-bot-token"
PASSWORD = "abcd efgh ijkl mnop"


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {"ok": True}
        self.content = b"x"
        self.reason = "OK" if status_code == 200 else "Bad Request"

    def json(self):
        return self._body


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.sent = []
        self.logged_in = None
        self.tls = False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, message):
        self.sent.append(message)


@pytest.fixture
def channels_configured(monkeypatch):
    s = "app.core.notify.settings"
    for name, value in {
        "telegram_bot_token": TOKEN,
        "telegram_chat_id": "42",
        "smtp_username": "me@gmail.com",
        "smtp_password": PASSWORD,
        "digest_email_to": "me@gmail.com",
    }.items():
        monkeypatch.setattr(f"{s}.{name}", value)
    monkeypatch.setattr("app.services.digest_service.settings.digest_telegram_enabled", True)
    monkeypatch.setattr("app.services.digest_service.settings.digest_email_enabled", True)
    FakeSMTP.instances = []


@pytest.fixture
def telegram_posts(monkeypatch):
    posts: list[dict] = []

    def _post(url, json=None, timeout=None):
        posts.append({"url": url, **json})
        return FakeResponse()

    monkeypatch.setattr("app.core.notify.requests.post", _post)
    return posts


@pytest.fixture
def fake_smtp(monkeypatch):
    monkeypatch.setattr("app.core.notify.smtplib.SMTP", FakeSMTP)
    return FakeSMTP


def _seed(db_session) -> list[Job]:
    jobs = [
        make_job(
            title="Great Match",
            company="Acme <Labs>",
            llm_score=90,
            llm_reason="Python + React",
            fresher_friendly=True,
        ),
        make_job(
            title="Good Match", company="Beta", llm_score=60, llm_reason="ok", red_flags=["Mentions a fee"]
        ),
        make_job(title="Poor Match", company="Gamma", llm_score=20, llm_reason="Java only"),
        make_job(title="Unscored", company="Delta", rule_score=75),
        make_job(title="Filtered", company="Eps", passed_prefilter=False, llm_score=95),
        make_job(title="Already sent", company="Zeta", llm_score=99, digested_at=datetime.now(UTC)),
        make_job(
            title="Stale", company="Eta", llm_score=88, first_seen_at=datetime.now(UTC) - timedelta(days=30)
        ),
    ]
    db_session.add_all(jobs)
    db_session.commit()
    return jobs


def test_selection_ranks_ai_scores_then_tops_up_with_rule_scored(db_session):
    _seed(db_session)
    titles = [j.title for j in digest_service.select_digest_jobs(db_session, top_n=10)]
    assert titles == ["Great Match", "Good Match", "Unscored"]
    assert [j.title for j in digest_service.select_digest_jobs(db_session, top_n=1)] == ["Great Match"]


def test_digest_sends_to_both_channels_and_marks_jobs(
    db_session, channels_configured, telegram_posts, fake_smtp
):
    _seed(db_session)
    result = digest_service.run_digest(db_session)

    assert result.channels == {"telegram": "sent", "email": "sent"}
    assert result.sent_items == 3

    text = telegram_posts[0]["text"]
    assert telegram_posts[0]["url"] == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert telegram_posts[0]["chat_id"] == "42" and telegram_posts[0]["parse_mode"] == "HTML"
    assert "Acme &lt;Labs&gt;" in text  # HTML-escaped
    assert "90/100" in text and "75/100 (rule)" in text
    assert "Mentions a fee" in text
    assert "http://localhost:5173/jobs/" in text

    smtp = fake_smtp.instances[0]
    assert smtp.tls and smtp.logged_in == ("me@gmail.com", PASSWORD)
    message = smtp.sent[0]
    assert "3 matches" in message["Subject"]
    html_part = message.get_body(preferencelist=("html",)).get_content()
    for header in ("Title", "Company", "Location", "Score", "Why", "Red flags", "Links"):
        assert f">{header}</th>" in html_part
    assert "Apply</a>" in html_part and "Open in app</a>" in html_part

    # Delivered → never sent again.
    assert digest_service.select_digest_jobs(db_session) == []


def test_one_channel_failing_does_not_stop_the_other(db_session, channels_configured, fake_smtp, monkeypatch):
    _seed(db_session)

    def _telegram_down(url, json=None, timeout=None):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}")

    monkeypatch.setattr("app.core.notify.requests.post", _telegram_down)
    result = digest_service.run_digest(db_session)

    assert result.channels["email"] == "sent"
    assert result.channels["telegram"].startswith("failed:")
    assert result.delivered
    assert digest_service.select_digest_jobs(db_session) == []


def test_email_failure_with_telegram_working(db_session, channels_configured, telegram_posts, monkeypatch):
    _seed(db_session)

    class BrokenSMTP(FakeSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")

    monkeypatch.setattr("app.core.notify.smtplib.SMTP", BrokenSMTP)
    result = digest_service.run_digest(db_session)
    assert result.channels["telegram"] == "sent"
    assert "535" in result.channels["email"]


def test_nothing_delivered_keeps_jobs_queued(db_session, channels_configured, monkeypatch):
    _seed(db_session)
    monkeypatch.setattr(
        "app.core.notify.requests.post",
        lambda *a, **k: FakeResponse(401, {"ok": False, "description": "Unauthorized"}),
    )
    monkeypatch.setattr("app.services.digest_service.settings.digest_email_enabled", False)

    result = digest_service.run_digest(db_session)
    assert not result.delivered
    assert result.channels == {
        "telegram": "failed: Telegram API error 401: Unauthorized",
        "email": "disabled",
    }
    assert len(digest_service.select_digest_jobs(db_session)) == 3  # retried tomorrow


def test_disabled_and_unconfigured_channels_are_reported_not_attempted(db_session, monkeypatch):
    monkeypatch.setattr("app.services.digest_service.settings.digest_telegram_enabled", True)
    monkeypatch.setattr("app.core.notify.settings.telegram_bot_token", "your-telegram-bot-token-here")
    result = digest_service.run_digest(db_session)
    assert result.channels == {"telegram": "not configured", "email": "disabled"}


def test_secrets_never_appear_in_errors_or_logs(db_session, channels_configured, caplog, monkeypatch):
    _seed(db_session)

    def _telegram_down(url, json=None, timeout=None):
        raise requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}")

    class BrokenSMTP(FakeSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, f"bad credentials {password}".encode())

    monkeypatch.setattr("app.core.notify.requests.post", _telegram_down)
    monkeypatch.setattr("app.core.notify.smtplib.SMTP", BrokenSMTP)

    with caplog.at_level(logging.DEBUG):
        result = digest_service.run_digest(db_session)

    everything = caplog.text + repr(result.channels)
    assert TOKEN not in everything
    assert PASSWORD not in everything
    assert "***" in result.channels["telegram"]


def test_test_digest_uses_configured_channels_even_if_disabled_and_marks_nothing(
    db_session, channels_configured, telegram_posts, fake_smtp, monkeypatch
):
    monkeypatch.setattr("app.services.digest_service.settings.digest_telegram_enabled", False)
    monkeypatch.setattr("app.services.digest_service.settings.digest_email_enabled", False)
    _seed(db_session)

    result = digest_service.run_test_digest(db_session)

    assert result.channels == {"telegram": "sent", "email": "sent"}
    assert telegram_posts[0]["text"].startswith("<b>[TEST] Job digest")
    assert len(digest_service.select_digest_jobs(db_session)) == 3  # nothing marked as sent


def test_test_digest_sends_sample_when_db_is_empty(
    db_session, channels_configured, telegram_posts, fake_smtp
):
    result = digest_service.run_test_digest(db_session)
    assert result.delivered
    assert "Software Engineer (sample)" in telegram_posts[0]["text"]


def test_long_telegram_digest_is_split_without_breaking_items():
    blocks = [f"<b>{i}</b> " + "x" * 900 for i in range(10)]
    chunks = notify.split_for_telegram("\n\n".join(blocks))
    assert len(chunks) > 1
    assert all(len(c) <= notify.TELEGRAM_MAX_CHARS for c in chunks)
    assert sum(c.count("<b>") for c in chunks) == 10


def test_posted_label():
    from datetime import UTC, datetime, timedelta

    from app.services.digest_service import posted_label

    now = datetime(2026, 10, 9, 9, tzinfo=UTC)
    assert posted_label(None, now) == "posting date not given"
    assert posted_label(now, now) == "posted today"
    assert posted_label((now - timedelta(days=3)).replace(tzinfo=None), now) == "posted 3d ago"
