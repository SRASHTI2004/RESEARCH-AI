from urllib.parse import unquote_plus

from app.core.profile import Profile
from app.services import referral_service
from tests.factories import make_job


def _kit(profile, **job_overrides):
    return referral_service.build_referral_kit(make_job(**job_overrides), profile)


def test_search_strings_cover_alumni_role_and_recruiters(profile):
    kit = _kit(profile, title="Software Engineer, Backend (Python)", company="Acme")
    queries = [s.query for s in kit.search_strings]

    assert '"Acme" "Test Institute of Technology"' in queries
    assert '"Acme" "Software Engineer"' in queries  # team noise stripped
    assert any("recruiter" in q for q in queries)
    assert any(q.startswith("site:linkedin.com/in") for q in queries)
    for s in kit.search_strings:
        # Links only open a search page in the user's browser — no fetching.
        assert s.url.startswith(
            ("https://www.linkedin.com/search/results/people/", "https://www.google.com/search")
        )
        assert s.query in unquote_plus(s.url)


def test_without_college_alumni_searches_are_skipped_with_a_hint():
    kit = _kit(Profile(name="A", primary_skills=["Python"]))
    assert all("alumni" not in s.label.lower() for s in kit.search_strings)
    assert any("Add `college`" in item for item in kit.checklist)


def test_drafts_only_use_facts_from_profile_and_posting(profile):
    kit = _kit(
        profile, title="Junior Developer", company="Acme", description="We use React and Python daily. " * 10
    )
    drafts = {d.kind: d for d in kit.drafts}

    assert set(drafts) == {"referral_ask", "connection_note", "recruiter_intro", "follow_up"}
    ask = drafts["referral_ask"].body
    assert "Test User" in ask and "Test Institute of Technology" in ask
    assert "Junior Developer" in ask and "Acme" in ask
    assert "https://boards.greenhouse.io/acme/jobs/1" in ask
    # Only skills that the posting mentions AND the profile lists.
    assert "Python, React" in ask
    assert "TypeScript" not in ask and "Docker" not in ask
    # Recipient name is a placeholder for the user to fill — never guessed.
    assert ask.startswith("Hi [Name]")


def test_connection_note_respects_linkedin_limit(profile):
    long_title = (
        "Associate Software Development Engineer, Platform Infrastructure and Developer Experience " * 3
    )
    kit = _kit(profile, title=long_title, company="A Very Long Company Name Private Limited")
    note = next(d for d in kit.drafts if d.kind == "connection_note")
    assert note.char_count == len(note.body) <= referral_service.LINKEDIN_NOTE_LIMIT


def test_missing_name_and_no_skill_overlap_are_flagged():
    kit = _kit(Profile(primary_skills=["Elixir"]), description="Java and Spring only. " * 20)
    assert any("Set `name`" in n for n in kit.notes)
    assert any("None of your profile skills" in n for n in kit.notes)
    assert "[Your name]" in kit.drafts[0].body


def test_role_keyword():
    assert referral_service.role_keyword("Software Engineer - Winter Intern") == "Software Engineer"
    assert referral_service.role_keyword("Frontend Engineer, Vision") == "Frontend Engineer"
    assert referral_service.role_keyword("") == "Software Engineer"


def test_referral_endpoint(client, auth_headers, db_session):
    job = make_job()
    db_session.add(job)
    db_session.commit()

    res = client.get(f"/jobs/{job.id}/referral", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["search_strings"] and data["checklist"] and len(data["drafts"]) == 4
    assert client.get("/jobs/missing/referral", headers=auth_headers).status_code == 404
    assert client.get(f"/jobs/{job.id}/referral").status_code == 401
