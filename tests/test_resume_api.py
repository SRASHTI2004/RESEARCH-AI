from tests.factories import make_job


def _job(db_session):
    job = make_job(title="Backend Developer", description="Python FastAPI PostgreSQL pytest role. " * 5)
    db_session.add(job)
    db_session.commit()
    return job


def test_master_status_reports_missing_file(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.resume.settings.master_resume_path", "data/private/does-not-exist.yaml")
    data = client.get("/resume/master", headers=auth_headers).json()
    assert data["exists"] is False
    assert "data/master_resume.example.yaml" in data["message"]


def test_master_status_with_resume(client, auth_headers):
    data = client.get("/resume/master", headers=auth_headers).json()
    assert data == {
        "exists": True,
        "message": "",
        "name": "Your Name",
        "experience": 1,
        "projects": 1,
        "skills": 12,
    }


def test_tailor_requires_master_resume(client, auth_headers, db_session, monkeypatch):
    job = _job(db_session)
    monkeypatch.setattr("app.core.resume.settings.master_resume_path", "data/private/does-not-exist.yaml")
    res = client.post(f"/jobs/{job.id}/tailored-resumes", headers=auth_headers)
    assert res.status_code == 409


def test_tailor_list_get_export_delete(client, auth_headers, db_session):
    job = _job(db_session)
    # The suite-wide LLM mock returns prose, so this exercises the reorder-only fallback.
    res = client.post(f"/jobs/{job.id}/tailored-resumes", headers=auth_headers)
    assert res.status_code == 201
    created = res.json()
    assert created["used_llm"] is False
    assert created["content"]["contact"]["name"] == "Your Name"
    assert "fastapi" in created["keywords_matched"]
    assert created["diff"]

    listed = client.get(f"/jobs/{job.id}/tailored-resumes", headers=auth_headers).json()
    assert [r["id"] for r in listed] == [created["id"]]
    assert client.get(f"/tailored-resumes/{created['id']}", headers=auth_headers).status_code == 200

    pdf = client.get(f"/tailored-resumes/{created['id']}/export?format=pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert 'filename="Your_Name_Acme_resume.pdf"' in pdf.headers["content-disposition"]
    assert pdf.headers["cache-control"] == "no-store"

    docx = client.get(f"/tailored-resumes/{created['id']}/export?format=docx", headers=auth_headers)
    assert docx.status_code == 200 and docx.content[:2] == b"PK"  # a .docx is a zip

    assert (
        client.get(f"/tailored-resumes/{created['id']}/export?format=exe", headers=auth_headers).status_code
        == 422
    )
    assert client.delete(f"/tailored-resumes/{created['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/tailored-resumes/{created['id']}", headers=auth_headers).status_code == 404


def test_tailored_resumes_are_owner_only(client, make_user_headers, db_session):
    job = _job(db_session)
    alice = make_user_headers("alice@example.com")
    admin = make_user_headers("boss@example.com", admin=True)
    created = client.post(f"/jobs/{job.id}/tailored-resumes", headers=alice).json()

    assert client.get(f"/tailored-resumes/{created['id']}", headers=admin).status_code == 404
    assert client.get(f"/tailored-resumes/{created['id']}/export", headers=admin).status_code == 404
    assert client.get(f"/jobs/{job.id}/tailored-resumes", headers=admin).json() == []
