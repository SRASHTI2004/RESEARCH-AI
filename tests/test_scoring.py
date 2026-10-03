import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.llm import LLMError
from app.models.job import Job
from app.services import scoring_service
from tests.factories import make_job


def _seed(db_session, n: int, **overrides) -> list[Job]:
    jobs = [make_job(title=f"Engineer {chr(65 + i)}", rule_score=50 + i, **overrides) for i in range(n)]
    db_session.add_all(jobs)
    db_session.commit()
    return jobs


def _fake_llm(scores_by_title: dict[str, int] | None = None, calls: list[str] | None = None):
    """Answers each batch prompt with a JSON score per job key found in it."""

    def _invoke(prompt, *, temperature=0.3, stage="default"):
        if calls is not None:
            calls.append(prompt)
        entries = []
        for line in prompt.splitlines():
            if line.startswith("[J"):
                key = line[1 : line.index("]")]
                title = line[line.index("]") + 2 : line.index(" at ")]
                score = (scores_by_title or {}).get(title, 70)
                entries.append(
                    {"id": key, "score": score, "reason": f"fits {title}", "fresher_friendly": True}
                )
        return "Here you go:\n```json\n" + json.dumps(entries) + "\n```"

    return _invoke


def test_selects_only_top_unscored_recent_passing_jobs(db_session):
    _seed(db_session, 4)
    db_session.add_all(
        [
            make_job(title="Rejected", passed_prefilter=False, rule_score=99),
            make_job(title="Already scored", llm_score=80, rule_score=98),
            make_job(title="Old", rule_score=97, first_seen_at=datetime.now(UTC) - timedelta(days=30)),
        ]
    )
    db_session.commit()

    picked = scoring_service.select_for_scoring(db_session, limit=3)
    assert [j.title for j in picked] == ["Engineer D", "Engineer C", "Engineer B"]


def test_scores_in_batches_and_stores_results(db_session, profile, monkeypatch):
    jobs = _seed(db_session, 7)
    calls: list[str] = []
    monkeypatch.setattr("app.core.llm.invoke_llm", _fake_llm({"Engineer A": 91}, calls))
    monkeypatch.setattr("app.services.scoring_service.settings.scoring_batch_size", 3)
    sleeps: list[float] = []
    monkeypatch.setattr("app.services.scoring_service._sleep", sleeps.append)

    summary = scoring_service.score_jobs(db_session, profile, jobs)

    assert summary.scored == 7 and summary.failed_batches == 0
    assert len(calls) == 3  # 7 jobs / batch of 3
    assert len(sleeps) == 2  # pause between calls, not before the first
    db_session.refresh(jobs[0])
    assert jobs[0].llm_score == 91
    assert jobs[0].llm_reason == "fits Engineer A"
    assert jobs[0].fresher_friendly is True
    assert jobs[0].scored_at is not None
    assert jobs[0].score == 91  # LLM score takes precedence over rule score


def test_prompt_contains_profile_and_job(profile):
    prompt = scoring_service.build_prompt(profile, [("J1", make_job())])
    assert "Python, React, TypeScript, FastAPI" in prompt
    assert "[J1] Software Engineer at Acme" in prompt


def test_excerpt_keeps_intro_and_decisive_lines_within_limit():
    boilerplate = "\n".join(f"Our company culture value number {i} is about teamwork." for i in range(60))
    description = (
        "Build our web platform with React.\n"
        + boilerplate
        + "\nMinimum eligibility criteria\n- 2027 graduates only\n- CGPA 8 and above\n"
        + "Perks: snacks and a gym.\n"
    )
    text = scoring_service.excerpt(description)

    assert len(text) <= scoring_service.DESCRIPTION_CHARS
    assert text.startswith("Build our web platform with React.")
    assert "2027 graduates only" in text  # would be cut by a plain prefix
    assert "Minimum eligibility criteria" in text
    assert "snacks" not in text


def test_short_descriptions_are_passed_through_unchanged():
    assert scoring_service.excerpt("short and sweet") == "short and sweet"


@pytest.mark.parametrize(
    "raw",
    [
        '[{"id": "J1", "score": 50}]',
        '```json\n[{"id":"J1","score":50}]\n```',
        'Sure! [{"id":"J1","score":50}] ok',
    ],
)
def test_parse_scores_tolerates_wrapping(raw):
    assert scoring_service.parse_scores(raw)[0]["score"] == 50


def test_parse_scores_rejects_non_json():
    with pytest.raises(ValueError):
        scoring_service.parse_scores("I can't help with that")


def test_scores_are_clamped_and_unknown_ids_ignored(db_session, profile, monkeypatch):
    jobs = _seed(db_session, 1)
    monkeypatch.setattr(
        "app.core.llm.invoke_llm",
        lambda prompt,
        **kw: '[{"id":"J1","score":150,"reason":"r"},{"id":"J9","score":10},{"id":"J1","score":"bad"}]',
    )
    scoring_service.score_jobs(db_session, profile, jobs)
    assert jobs[0].llm_score == 100


def test_bad_batch_leaves_jobs_unscored_and_stops_after_repeated_failures(db_session, profile, monkeypatch):
    jobs = _seed(db_session, 15)
    calls = []

    def _down(prompt, **kw):
        calls.append(prompt)
        raise LLMError("All configured LLM providers failed: gemini: rate limited")

    monkeypatch.setattr("app.core.llm.invoke_llm", _down)
    summary = scoring_service.score_jobs(db_session, profile, jobs)

    assert summary.scored == 0
    assert len(calls) == scoring_service.MAX_CONSECUTIVE_FAILURES  # didn't burn all 3 batches
    assert all(j.llm_score is None for j in jobs)  # retried next run


def test_default_mock_llm_output_is_handled_gracefully(db_session, profile):
    """The suite-wide mock returns prose, not JSON — scoring must not crash."""
    jobs = _seed(db_session, 2)
    summary = scoring_service.run_scoring(db_session, profile)
    assert summary.scored == 0 and summary.failed_batches == 1
    assert jobs[0].llm_score is None
