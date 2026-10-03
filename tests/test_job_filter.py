from datetime import UTC, datetime, timedelta

import pytest

from app.core.profile import LocationPrefs, Profile
from app.services import job_filter
from tests.factories import GOOD_DESCRIPTION


def _evaluate(profile, **overrides):
    args = {
        "title": "Software Engineer",
        "description": GOOD_DESCRIPTION,
        "location": "Bengaluru, India",
        "is_remote": False,
        "tags": [],
        "official_source": True,
        "posted_at": datetime.now(UTC),
        "profile": profile,
    }
    args.update(overrides)
    return job_filter.evaluate(**args)


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer",
        "Sr. Backend Developer",
        "Lead Frontend Engineer",
        "Staff Engineer",
        "Engineering Manager",
        "Principal Developer",
        "Software Engineer III",
        "SDE 2 Infra",
        "Data Engineer II",
        "Engineer 3 - Business Systems",
    ],
)
def test_seniority_titles_are_rejected(profile, title):
    result = _evaluate(profile, title=title)
    assert not result.passed
    assert "seniority" in result.reason or "mid-level" in result.reason


@pytest.mark.parametrize(
    "title",
    [
        "Account Executive",
        "Marketing Intern",
        "Sales Engineer",
        "Recruiter",
        "Video Editor Intern",
        "Copy Intern",
    ],
)
def test_non_dev_titles_are_rejected(profile, title):
    assert not _evaluate(profile, title=title).passed


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Requires 5+ years of experience in Python.", 5),
        ("3-5 yrs experience with React", 3),
        ("We were founded 10 years ago. 1+ years experience preferred.", 1),
        ("No experience requirement mentioned.", None),
        ("2+ years of Python experience and 6+ years experience overall", 2),
    ],
)
def test_min_years_required(text, expected):
    assert job_filter.min_years_required(text) == expected


def test_too_many_years_rejected(profile):
    result = _evaluate(profile, description="You have 4+ years of professional experience building APIs.")
    assert not result.passed
    assert "4+ years" in result.reason


@pytest.mark.parametrize(
    ("location", "is_remote", "passes"),
    [
        ("Pune, India", False, True),
        ("Hyderabad", False, True),
        ("Remote - India", True, True),
        ("Worldwide", True, True),
        ("Anywhere in the World", True, True),
        ("", True, True),
        ("Remote, Global", True, True),
        ("Remote - EMEA/APAC", True, True),
        ("Remote (US)", True, False),
        ("Foster City, CA", True, False),
        ("Pakistan", True, False),
        ("USA, Canada", True, False),
        ("Europe", True, False),
        ("San Francisco, CA", False, False),
        ("Berlin", False, False),
    ],
)
def test_location_rules(profile, location, is_remote, passes):
    assert _evaluate(profile, location=location, is_remote=is_remote).passed is passes


def test_india_onsite_outside_preferred_cities_rejected_when_strict():
    strict = Profile(locations=LocationPrefs(preferred_cities=["Pune"], accept_any_india_city=False))
    assert not _evaluate(strict, location="Chennai, India").passed
    assert _evaluate(strict, location="Pune, India").passed
    assert _evaluate(strict, location="Remote, India", is_remote=True).passed


def test_global_remote_can_be_disabled():
    india_only = Profile(locations=LocationPrefs(open_to_global_remote=False))
    assert not _evaluate(india_only, location="Worldwide", is_remote=True).passed
    assert _evaluate(india_only, location="Remote - India", is_remote=True).passed


def test_rule_score_rewards_stack_junior_signals_city_and_recency(profile):
    strong = _evaluate(profile, title="Junior Full Stack Developer", location="Pune")
    weak = _evaluate(
        profile,
        title="Software Engineer",
        description="Build Go and Rust services for our platform. " * 10,
        location="Remote",
        is_remote=True,
        official_source=False,
        posted_at=datetime.now(UTC) - timedelta(days=30),
    )
    assert strong.passed and weak.passed
    assert strong.rule_score > weak.rule_score
    assert 0 <= weak.rule_score <= strong.rule_score <= 100


@pytest.mark.parametrize(
    "title", ["Software Engineer - New Grad (2027)", "Software Engineer Intern", "SDE Intern", "SDE 1"]
)
def test_fresher_titles_pass(profile, title):
    assert _evaluate(profile, title=title).passed


def test_naive_datetimes_from_sqlite_are_handled(profile):
    naive = datetime.now(UTC).replace(tzinfo=None)
    assert _evaluate(profile, posted_at=naive).passed
