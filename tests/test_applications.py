from datetime import date, timedelta

from app.models.application import Application
from app.models.user import User
from app.services import digest_service
from tests.factories import make_job


def _job(db_session, **overrides):
    job = make_job(**overrides)
    db_session.add(job)
    db_session.commit()
    return job


def test_requires_auth(client):
    assert client.get("/applications").status_code == 401


def test_save_job_copies_details_and_is_idempotent(client, auth_headers, db_session):
    job = _job(db_session, llm_score=81)
    res = client.post("/applications", json={"job_id": job.id}, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Software Engineer" and data["company"] == "Acme"
    assert data["url"] == job.url
    assert data["status"] == "saved"
    assert data["job_score"] == 81
    assert data["follow_up_on"] is None  # "saved" gets no default reminder

    again = client.post("/applications", json={"job_id": job.id}, headers=auth_headers).json()
    assert again["id"] == data["id"]
    assert len(client.get("/applications", headers=auth_headers).json()["items"]) == 1


def test_manual_entry_and_validation(client, auth_headers):
    res = client.post(
        "/applications",
        json={"title": "Backend Intern", "company": "Found on a college group", "status": "applied"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["job_id"] is None
    assert res.json()["applied_on"] == date.today().isoformat()

    assert client.post("/applications", json={"title": "No company"}, headers=auth_headers).status_code == 422
    assert client.post("/applications", json={"job_id": "nope"}, headers=auth_headers).status_code == 404
    bad_status = client.post(
        "/applications", json={"title": "T", "company": "C", "status": "ghosted"}, headers=auth_headers
    )
    assert bad_status.status_code == 422


def test_status_change_sets_applied_date_and_default_follow_up(client, auth_headers, db_session):
    job = _job(db_session)
    app_id = client.post("/applications", json={"job_id": job.id}, headers=auth_headers).json()["id"]

    applied = client.patch(f"/applications/{app_id}", json={"status": "applied"}, headers=auth_headers).json()
    assert applied["applied_on"] == date.today().isoformat()
    assert applied["follow_up_on"] == (date.today() + timedelta(days=7)).isoformat()

    custom = (date.today() + timedelta(days=2)).isoformat()
    moved = client.patch(
        f"/applications/{app_id}",
        json={"status": "interview", "follow_up_on": custom, "notes": "Round 1 on Monday"},
        headers=auth_headers,
    ).json()
    assert moved["follow_up_on"] == custom
    assert moved["notes"] == "Round 1 on Monday"
    assert moved["applied_on"] == date.today().isoformat()  # kept

    cleared = client.patch(
        f"/applications/{app_id}", json={"follow_up_on": None}, headers=auth_headers
    ).json()
    assert cleared["follow_up_on"] is None
    assert cleared["status"] == "interview"


def test_filters_and_counts(client, auth_headers, db_session):
    today = date.today()
    ids = []
    for title, status, follow in [
        ("Overdue role", "applied", today - timedelta(days=2)),
        ("Due today", "referral_asked", today),
        ("Next week", "interview", today + timedelta(days=5)),
        ("Rejected old", "rejected", today - timedelta(days=10)),
        ("No reminder", "saved", None),
    ]:
        res = client.post(
            "/applications",
            json={
                "title": title,
                "company": "Co",
                "status": status,
                "follow_up_on": follow and follow.isoformat(),
            },
            headers=auth_headers,
        )
        ids.append(res.json()["id"])

    def titles(qs):
        return [a["title"] for a in client.get(f"/applications{qs}", headers=auth_headers).json()["items"]]

    assert titles("?due=overdue") == ["Overdue role"]
    assert titles("?due=today") == ["Overdue role", "Due today"]
    assert titles("?due=week") == ["Overdue role", "Due today", "Next week"]  # rejected excluded
    assert titles("?status=saved") == ["No reminder"]
    assert titles("?q=next") == ["Next week"]
    # Default order: soonest follow-up first, no-reminder last.
    assert titles("")[-1] == "No reminder"

    counts = client.get("/applications", headers=auth_headers).json()["counts"]
    assert counts == {"applied": 1, "referral_asked": 1, "interview": 1, "rejected": 1, "saved": 1}


def test_applications_are_private_even_from_admins(client, make_user_headers):
    alice = make_user_headers("alice@example.com")
    admin = make_user_headers("root@example.com", admin=True)
    app_id = client.post("/applications", json={"title": "T", "company": "C"}, headers=alice).json()["id"]

    assert client.get("/applications", headers=admin).json()["items"] == []
    assert client.patch(f"/applications/{app_id}", json={"notes": "x"}, headers=admin).status_code == 404
    assert client.delete(f"/applications/{app_id}", headers=admin).status_code == 404


def test_delete(client, auth_headers):
    app_id = client.post("/applications", json={"title": "T", "company": "C"}, headers=auth_headers).json()[
        "id"
    ]
    assert client.delete(f"/applications/{app_id}", headers=auth_headers).status_code == 204
    assert client.get("/applications", headers=auth_headers).json()["items"] == []


def test_digest_includes_due_follow_ups(db_session):
    user = User(email="me@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    today = date.today()
    db_session.add_all(
        [
            Application(
                owner_id=user.id, title="Ping recruiter", company="Acme", status="applied", follow_up_on=today
            ),
            Application(
                owner_id=user.id,
                title="Later",
                company="Beta",
                status="applied",
                follow_up_on=today + timedelta(days=3),
            ),
            Application(
                owner_id=user.id, title="Closed", company="Gamma", status="offer", follow_up_on=today
            ),
        ]
    )
    db_session.commit()

    follow_ups = digest_service.collect_follow_ups(db_session, today)
    assert [f.title for f in follow_ups] == ["Ping recruiter"]

    content = digest_service.DigestContent(items=[], follow_ups=follow_ups)
    assert "Ping recruiter" in digest_service.format_telegram(content)
    _, text, html = digest_service.format_email(content)
    assert "Follow-up due" in text and "Follow-ups due" in html
