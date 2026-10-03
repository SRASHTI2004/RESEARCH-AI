import json

from app import cli
from app.models.job import Job
from tests.factories import FakeSource, make_posting


def _wire(monkeypatch, testing_session_factory, profile, sources):
    monkeypatch.setattr("app.cli.SessionLocal", testing_session_factory)
    monkeypatch.setattr("app.cli.load_profile", lambda: profile)
    monkeypatch.setattr("app.services.daily_service.build_sources", lambda p: sources)
    monkeypatch.setattr("app.cli.build_sources", lambda p, names=None: sources)


def test_fetch_command(monkeypatch, testing_session_factory, profile, db_session, capsys):
    _wire(monkeypatch, testing_session_factory, profile, [FakeSource("greenhouse", [make_posting()])])
    assert cli.main(["fetch"]) == 0
    assert "1 new (1 pass the filter)" in capsys.readouterr().out
    assert db_session.query(Job).count() == 1


def test_run_daily_fetches_scores_and_reports_digest_channels(
    monkeypatch, testing_session_factory, profile, db_session, capsys
):
    _wire(monkeypatch, testing_session_factory, profile, [FakeSource("greenhouse", [make_posting()])])
    monkeypatch.setattr(
        "app.core.llm.invoke_llm",
        lambda prompt, **kw: json.dumps(
            [{"id": "J1", "score": 77, "reason": "good", "fresher_friendly": True}]
        ),
    )

    code = cli.main(["run-daily"])

    out = capsys.readouterr().out
    assert code == 0
    assert "Fetch: 1 new jobs" in out
    assert "Score: 1/1 scored" in out
    assert "telegram  disabled" in out and "email     disabled" in out
    job = db_session.query(Job).one()
    assert job.llm_score == 77
    assert job.digested_at is None  # no channel delivered → still queued


def test_run_daily_survives_a_failing_source_and_llm_outage(
    monkeypatch, testing_session_factory, profile, db_session, capsys
):
    _wire(
        monkeypatch, testing_session_factory, profile, [FakeSource("remotive", error=RuntimeError("timeout"))]
    )
    assert cli.main(["run-daily"]) == 0
    assert "source FAILED remotive: timeout" in capsys.readouterr().out


def test_test_digest_exit_code_reflects_delivery(monkeypatch, testing_session_factory, capsys):
    monkeypatch.setattr("app.cli.SessionLocal", testing_session_factory)
    assert cli.main(["test-digest"]) == 1  # nothing configured in tests
    assert "not configured" in capsys.readouterr().out
