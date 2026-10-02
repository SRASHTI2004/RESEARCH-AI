from app.core.llm import LLMError


def test_research_happy_path(client):
    res = client.post("/research", json={"topic": "Acme Corp"})
    assert res.status_code == 200

    data = res.json()
    assert data["topic"] == "Acme Corp"
    assert data["status"] == "done"
    assert data["error"] is None
    for field in ("research", "analysis", "report", "final_report"):
        assert "MOCKED" in data[field]


def test_research_blank_topic_rejected(client):
    res = client.post("/research", json={"topic": "   "})
    assert res.status_code == 422


def test_research_missing_topic_rejected(client):
    res = client.post("/research", json={})
    assert res.status_code == 422


def test_research_llm_failure_returns_502(client, monkeypatch):
    def _boom(prompt, *, temperature=0.3, stage="default"):
        raise LLMError("all providers exhausted")

    monkeypatch.setattr("app.core.llm.invoke_llm", _boom)

    res = client.post("/research", json={"topic": "Acme Corp"})
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
