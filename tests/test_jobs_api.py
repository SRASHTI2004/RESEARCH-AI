from datetime import UTC, datetime, timedelta

from app.models.job import SourceRun
from tests.factories import make_job


def _seed(db_session):
    db_session.add_all(
        [
            make_job(title="Software Engineer", company="Acme", rule_score=80),
            make_job(title="Junior Backend Developer", company="Beta", rule_score=60, source="remotive"),
            make_job(
                title="Senior Engineer",
                company="Gamma",
                passed_prefilter=False,
                prefilter_reason="seniority keyword in title ('Senior')",
                rule_score=0,
            ),
            make_job(
                title="Old Frontend Role",
                company="Delta",
                rule_score=70,
                first_seen_at=datetime.now(UTC) - timedelta(days=30),
            ),
        ]
    )
    db_session.commit()


def test_jobs_require_auth(client):
    assert client.get("/jobs").status_code == 401


def test_list_hides_filtered_out_jobs_by_default_and_sorts_by_score(client, auth_headers, db_session):
    _seed(db_session)
    data = client.get("/jobs", headers=auth_headers).json()
    assert data["total"] == 3
    assert [j["company"] for j in data["items"]] == ["Acme", "Delta", "Beta"]

    all_jobs = client.get("/jobs?include_filtered=true", headers=auth_headers).json()
    assert all_jobs["total"] == 4


def test_list_filters(client, auth_headers, db_session):
    _seed(db_session)
    assert client.get("/jobs?source=remotive", headers=auth_headers).json()["total"] == 1
    assert client.get("/jobs?q=backend", headers=auth_headers).json()["total"] == 1
    assert client.get("/jobs?min_score=65", headers=auth_headers).json()["total"] == 2
    recent = client.get("/jobs?days=7", headers=auth_headers).json()
    assert "Delta" not in [j["company"] for j in recent["items"]]


def test_job_detail_and_404(client, auth_headers, db_session):
    job = make_job()
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/jobs/{job.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["description"].startswith("We are hiring")
    assert client.get("/jobs/nope", headers=auth_headers).status_code == 404


def test_source_status_returns_latest_run_per_source(client, auth_headers, db_session):
    db_session.add_all(
        [
            SourceRun(
                source="remotive",
                status="error",
                message="old",
                started_at=datetime.now(UTC) - timedelta(days=1),
            ),
            SourceRun(source="remotive", status="ok", fetched_count=12),
            SourceRun(source="lever", status="ok", fetched_count=3),
        ]
    )
    db_session.commit()
    runs = client.get("/jobs/sources", headers=auth_headers).json()
    assert [(r["source"], r["status"]) for r in runs] == [("lever", "ok"), ("remotive", "ok")]
