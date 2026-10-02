from app.core.llm import LLMError


def test_research_requires_auth(client):
    res = client.post("/research", json={"company": "Acme Corp"})
    assert res.status_code == 401


def test_research_happy_path(client, auth_headers):
    res = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    assert res.status_code == 201

    data = res.json()
    assert data["company"] == "Acme Corp"
    assert data["status"] == "done"
    assert data["error"] is None
    assert data["id"]
    assert data["created_at"]
    for field in ("research", "analysis", "report", "final_report"):
        assert "MOCKED" in data[field]

    assert len(data["sources"]) == 2
    assert data["sources"][0]["url"] == "https://acme.example.com"
    assert "content" not in data["sources"][0]  # internal field, not exposed via API


def test_research_blank_company_rejected(client, auth_headers):
    res = client.post("/research", json={"company": "   "}, headers=auth_headers)
    assert res.status_code == 422


def test_research_missing_company_rejected(client, auth_headers):
    res = client.post("/research", json={}, headers=auth_headers)
    assert res.status_code == 422


def test_research_no_sources_found_returns_502(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.pipeline.agents.researcher.gather_sources", lambda company, **kw: [])

    res = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    assert res.status_code == 502
    assert "No web sources" in res.json()["detail"]


def test_research_llm_failure_returns_502(client, auth_headers, monkeypatch):
    def _boom(prompt, *, temperature=0.3, stage="default"):
        raise LLMError("all providers exhausted")

    monkeypatch.setattr("app.core.llm.invoke_llm", _boom)

    res = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    assert res.status_code == 502
    assert "all providers exhausted" in res.json()["detail"]


def test_research_failure_short_circuits_remaining_stages(monkeypatch):
    """If the researcher stage fails, analyzer/writer/reviewer must not run."""
    from app.pipeline.graph import run_research

    def _boom(prompt, *, temperature=0.3, stage="default"):
        raise LLMError("down")

    monkeypatch.setattr("app.core.llm.invoke_llm", _boom)

    result = run_research("Acme Corp")
    assert result["status"] == "failed"
    assert result["analysis"] == ""
    assert result["report"] == ""
    assert result["final_report"] == ""


def test_get_research_by_id_returns_persisted_job(client, auth_headers):
    created = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers).json()

    res = client.get(f"/research/{created['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["company"] == "Acme Corp"


def test_get_research_unknown_id_returns_404(client, auth_headers):
    res = client.get("/research/does-not-exist", headers=auth_headers)
    assert res.status_code == 404


def test_failed_job_is_persisted_and_retrievable(client, auth_headers, monkeypatch):
    """A 502 response to the client must not mean the job vanished — it's
    saved with status=failed so it shows up in history."""

    def _boom(prompt, *, temperature=0.3, stage="default"):
        raise LLMError("down")

    monkeypatch.setattr("app.core.llm.invoke_llm", _boom)

    create_res = client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    assert create_res.status_code == 502

    jobs = client.get("/research", headers=auth_headers).json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "failed"

    job = client.get(f"/research/{jobs[0]['id']}", headers=auth_headers).json()
    assert job["status"] == "failed"
    assert job["error"]


def test_list_research_orders_newest_first(client, auth_headers):
    client.post("/research", json={"company": "Acme Corp"}, headers=auth_headers)
    client.post("/research", json={"company": "Beta Inc"}, headers=auth_headers)

    jobs = client.get("/research", headers=auth_headers).json()
    assert [j["company"] for j in jobs] == ["Beta Inc", "Acme Corp"]


def test_user_cannot_see_another_users_job(client, make_user_headers):
    alice = make_user_headers("alice@example.com")
    bob = make_user_headers("bob@example.com")

    alice_job = client.post("/research", json={"company": "Acme Corp"}, headers=alice).json()

    # Bob's history is empty — Alice's job doesn't show up in it.
    assert client.get("/research", headers=bob).json() == []
    # And Bob can't fetch it directly either — 404, not 403, to avoid
    # confirming the job's existence to a non-owner.
    res = client.get(f"/research/{alice_job['id']}", headers=bob)
    assert res.status_code == 404


def test_admin_sees_every_users_job(client, make_user_headers):
    alice = make_user_headers("alice2@example.com")
    admin = make_user_headers("admin2@example.com", admin=True)

    client.post("/research", json={"company": "Acme Corp"}, headers=alice)

    jobs = client.get("/research", headers=admin).json()
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Acme Corp"
