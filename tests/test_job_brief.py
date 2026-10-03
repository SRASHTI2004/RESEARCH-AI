from tests.factories import make_job


def _job(db_session, company="Acme Corp"):
    job = make_job(company=company)
    db_session.add(job)
    db_session.commit()
    return job


def test_no_brief_yet_returns_null(client, auth_headers, db_session):
    job = _job(db_session)
    res = client.get(f"/jobs/{job.id}/brief", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() is None


def test_generate_brief_runs_research_pipeline_for_job_company(client, auth_headers, db_session):
    job = _job(db_session)
    res = client.post(f"/jobs/{job.id}/brief", headers=auth_headers)
    assert res.status_code == 202
    data = res.json()
    assert data["company"] == "Acme Corp"
    assert data["status"] == "done"  # eager Celery + mocked pipeline (conftest)
    assert "MOCKED" in data["final_report"]

    latest = client.get(f"/jobs/{job.id}/brief", headers=auth_headers).json()
    assert latest["id"] == data["id"]
    # Same pipeline as POST /research, so it's in the brief history too.
    assert data["id"] in [b["id"] for b in client.get("/research", headers=auth_headers).json()]


def test_existing_brief_matched_case_insensitively(client, auth_headers, db_session):
    job = _job(db_session, company="  acme corp ")
    brief = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers).json()
    assert client.get(f"/jobs/{job.id}/brief", headers=auth_headers).json()["id"] == brief["id"]


def test_briefs_are_per_user(client, make_user_headers, db_session):
    job = _job(db_session)
    alice = make_user_headers("alice@example.com")
    bob = make_user_headers("bob@example.com")
    client.post(f"/jobs/{job.id}/brief", headers=alice)
    assert client.get(f"/jobs/{job.id}/brief", headers=bob).json() is None


def test_brief_for_unknown_job_404s(client, auth_headers):
    assert client.post("/jobs/nope/brief", headers=auth_headers).status_code == 404
    assert client.get("/jobs/nope/brief", headers=auth_headers).status_code == 404


def test_brief_requires_auth(client, db_session):
    job = _job(db_session)
    assert client.post(f"/jobs/{job.id}/brief").status_code == 401
