from sqlalchemy import func, select

from app.core.config import settings
from app.models.application import Application
from app.models.job import Job
from app.models.research_job import ResearchJob
from app.services import demo_service, usage_service


def _count(db, model, *where):
    return db.scalar(select(func.count()).select_from(model).where(*where))


def test_public_config_reports_flags(client, monkeypatch):
    monkeypatch.setattr(settings, "registration_enabled", False)
    monkeypatch.setattr(settings, "demo_enabled", True)
    monkeypatch.setattr(settings, "llm_daily_action_limit", 5)

    assert client.get("/config").json() == {
        "registration_enabled": False,
        "demo_enabled": True,
        "llm_actions_left_today": 5,
    }


def test_demo_login_is_hidden_when_disabled(client):
    assert client.post("/auth/demo").status_code == 404


def test_demo_login_issues_working_tokens(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_enabled", True)

    tokens = client.post("/auth/demo").json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})

    assert me.status_code == 200
    assert me.json()["email"] == settings.demo_email


def test_registration_can_be_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "registration_enabled", False)

    response = client.post("/auth/register", json={"email": "new@example.com", "password": "password123"})

    assert response.status_code == 403


def test_seed_demo_is_idempotent_and_resets_visitor_changes(db_session, monkeypatch):
    monkeypatch.setattr(settings, "demo_enabled", True)

    first = demo_service.seed_demo(db_session)
    user = demo_service.get_or_create_demo_user(db_session)
    jobs_after_first = _count(db_session, Job)
    assert first.jobs_added == jobs_after_first > 0
    assert first.applications == 5

    # A visitor deletes a tracker entry and adds a brief of their own.
    db_session.delete(db_session.scalars(select(Application).where(Application.owner_id == user.id)).first())
    db_session.add(ResearchJob(company="Visitor Co", owner_id=user.id, status="done"))
    db_session.commit()

    second = demo_service.seed_demo(db_session)

    assert second.jobs_added == 0
    assert _count(db_session, Job) == jobs_after_first
    assert _count(db_session, Application, Application.owner_id == user.id) == 5
    assert _count(db_session, ResearchJob, ResearchJob.company == "Visitor Co") == 0


def test_sample_jobs_never_reach_a_digest(db_session, monkeypatch):
    monkeypatch.setattr(settings, "demo_enabled", True)
    demo_service.seed_demo(db_session)

    assert _count(db_session, Job, Job.digested_at.is_(None)) == 0


def test_daily_llm_budget_blocks_briefs_once_spent(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "llm_daily_action_limit", 1)

    first = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    second = client.post("/research", json={"company": "Beta Inc"}, headers=auth_headers)

    assert first.status_code == 202
    assert second.status_code == 429
    assert "per day" in second.json()["detail"]


def test_no_budget_means_unlimited(db_session, monkeypatch):
    monkeypatch.setattr(settings, "llm_daily_action_limit", 0)

    assert usage_service.remaining(db_session) is None
    usage_service.ensure_budget(db_session)  # does not raise
