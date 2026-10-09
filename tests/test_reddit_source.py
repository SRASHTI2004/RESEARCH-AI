import pytest

from app.core.config import settings
from app.core.jobsources import reddit
from app.core.jobsources.reddit import RedditSource, is_hiring_post


def _post(id_, title, flair=None, **extra):
    data = {
        "id": id_,
        "title": title,
        "link_flair_text": flair,
        "selftext": "We are a 20-person SaaS startup in Gurugram hiring a Python/React developer. " * 3,
        "permalink": f"/r/developersIndia/comments/{id_}/x/",
        "created_utc": 1791800000,
        "author": "founder_acme",
    }
    data.update(extra)
    return {"data": data}


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "reddit_client_id", "id")
    monkeypatch.setattr(settings, "reddit_client_secret", "secret")
    tokens = []

    def _post_form(url, data, auth):
        tokens.append((url, data, auth))
        return {"access_token": "tok"}

    monkeypatch.setattr("app.core.jobsources.http.post_form", _post_form)
    return tokens


@pytest.mark.parametrize(
    "title, flair, expected",
    [
        ("Python developer, 0-1 yrs, Gurugram", "Hiring", True),
        ("[Hiring] React intern, remote, paid", None, True),
        ("We're hiring backend engineers", None, True),
        ("[For Hire] Full stack dev available", None, False),
        ("Is hiring slow this year?", "General", False),
        ("Looking for work, open to work", "Hiring", False),
    ],
)
def test_is_hiring_post(title, flair, expected):
    assert is_hiring_post(title, flair) is expected


def test_skips_itself_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "reddit_client_id", "")
    assert not RedditSource().is_configured()


def test_fetch_keeps_only_hiring_posts_and_maps_them(monkeypatch, configured):
    seen = []

    def _get_json(url, params=None, headers=None):
        seen.append((url, headers))
        return {
            "data": {
                "children": [
                    _post("a1", "Junior Python Developer (Remote)", "Hiring"),
                    _post("a2", "[For Hire] Fresher seeking role", None),
                    _post("a3", "Rant about interviews", "Discussion"),
                    _post("a4", "[Hiring] pinned mod post", None, stickied=True),
                ]
            }
        }

    monkeypatch.setattr("app.core.jobsources.http.get_json", _get_json)
    jobs = RedditSource(["developersIndia"]).fetch()

    assert configured[0][0] == reddit.TOKEN_URL and configured[0][2] == ("id", "secret")
    assert seen[0][0].endswith("/r/developersIndia/new") and seen[0][1] == {"Authorization": "bearer tok"}
    assert [j.external_id for j in jobs] == ["a1"]
    job = jobs[0]
    assert job.company == "r/developersIndia · u/founder_acme"
    assert job.location == "India" and job.is_remote
    assert job.url == "https://www.reddit.com/r/developersIndia/comments/a1/x/"
    assert job.posted_at is not None and not job.official_source


def test_reddit_jobs_get_a_verify_flag(db_session, profile):
    from app.core.jobsources.base import NormalizedJob
    from app.services import job_ingest_service
    from app.services.job_ingest_service import IngestSummary

    posting = NormalizedJob(
        source="reddit",
        external_id="z9",
        title="Junior Python Developer",
        company="r/developersIndia · u/someone",
        url="https://www.reddit.com/r/developersIndia/comments/z9/x/",
        location="India",
        description="Python and React role at an early-stage startup. " * 6,
    )
    [job] = job_ingest_service.store(db_session, [posting], profile, IngestSummary())

    assert job.red_flags[0].startswith("Posted on Reddit by an individual")
