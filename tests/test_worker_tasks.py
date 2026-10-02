from app.repositories import research_repository as repo
from app.worker.tasks import run_research_job


def test_run_research_job_persists_status_after_each_stage(db_session, monkeypatch):
    """The whole point of streaming (vs. invoke()) is that the job row's
    status is updated after every stage completes, not just once at the
    end — this is what a polling frontend actually observes."""
    seen_statuses = []

    def _fake_invoke(prompt, *, temperature=0.3, stage="default"):
        # db_session and the task's own session share one physical SQLite
        # connection (StaticPool) — roll back db_session's read-only
        # transaction first so this SELECT sees the task's latest commits
        # instead of a stale snapshot from before this test's own setup.
        db_session.rollback()
        seen_statuses.append(repo.get_job(db_session, job.id).status)
        return f"MOCKED[{stage}]"

    monkeypatch.setattr("app.core.llm.invoke_llm", _fake_invoke)
    monkeypatch.setattr(
        "app.pipeline.agents.researcher.gather_sources",
        lambda company, **kw: [{"index": 1, "title": "T", "url": "https://u", "snippet": "s", "content": "c"}],
    )

    job = repo.create_job(db_session, "Acme Corp")
    run_research_job.run(job.id, "Acme Corp")  # call synchronously, bypassing Celery's task dispatch

    db_session.rollback()
    final = repo.get_job(db_session, job.id)
    assert final.status == "done"
    assert "MOCKED[reviewer]" in final.final_report

    # Before analyzer ran, researcher's status must already be persisted.
    assert seen_statuses == ["pending", "researching", "analyzing", "writing"]


def test_run_research_job_skips_silently_if_job_missing(db_session):
    """No job row (e.g. deleted mid-flight) must not raise — just a no-op."""
    run_research_job.run("does-not-exist", "Acme Corp")  # must not raise
