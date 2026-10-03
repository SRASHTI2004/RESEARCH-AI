"""Each source maps its real (trimmed) payload shape — captured from the
live APIs on 2026-10-03 — into NormalizedJob. No network: http is stubbed."""

import pytest

from app.core.jobsources import aggregators, ats
from app.core.jobsources.ats import WatchedCompany
from app.core.jobsources.base import job_fingerprint
from app.core.jobsources.text import html_to_text, parse_datetime


def _stub_json(monkeypatch, responses: dict[str, object]):
    calls: list[tuple[str, dict | None]] = []

    def _get_json(url, params=None):
        calls.append((url, params))
        for fragment, payload in responses.items():
            if fragment in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr("app.core.jobsources.http.get_json", _get_json)
    return calls


def test_greenhouse_maps_jobs_and_unescapes_content(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "boards/acme/jobs": {
                "jobs": [
                    {
                        "id": 42,
                        "title": "Software Engineer ",
                        "absolute_url": "https://acme.com/jobs?gh_jid=42",
                        "location": {"name": "Remote - India"},
                        "first_published": "2026-09-09T10:50:29-04:00",
                        "content": "&lt;p&gt;Build things with &lt;strong&gt;Python&lt;/strong&gt;&lt;/p&gt;",
                    }
                ]
            }
        },
    )
    jobs = ats.GreenhouseSource([WatchedCompany(name="Acme", ats="greenhouse", board="acme")]).fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Software Engineer"
    assert job.company == "Acme"
    assert job.external_id == "acme:42"
    assert job.is_remote is True
    assert job.official_source is True
    assert job.description == "Build things with Python"
    assert job.posted_at is not None and job.posted_at.year == 2026


def test_lever_combines_description_sections(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "postings/acme": [
                {
                    "id": "abc",
                    "text": "Backend Developer",
                    "hostedUrl": "https://jobs.lever.co/acme/abc",
                    "categories": {"location": "Pune", "commitment": "Full-time"},
                    "workplaceType": "onsite",
                    "descriptionPlain": "Intro text",
                    "lists": [{"text": "Requirements", "content": "<li>Python</li><li>SQL</li>"}],
                    "additionalPlain": "Benefits",
                    "createdAt": 1786469891368,
                }
            ]
        },
    )
    jobs = ats.LeverSource([WatchedCompany(name="Acme", ats="lever", board="acme")]).fetch()

    assert jobs[0].url == "https://jobs.lever.co/acme/abc"
    assert jobs[0].is_remote is False
    assert "Requirements" in jobs[0].description and "- Python" in jobs[0].description
    assert jobs[0].employment_type == "Full-time"
    assert jobs[0].posted_at is not None


def test_ashby_skips_unlisted_and_reads_compensation(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "job-board/acme": {
                "jobs": [
                    {
                        "id": "1",
                        "title": "Frontend Engineer",
                        "location": "Bengaluru",
                        "secondaryLocations": [{"location": "Remote (India)"}],
                        "isRemote": True,
                        "isListed": True,
                        "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                        "descriptionPlain": "React work",
                        "publishedAt": "2026-10-01T00:00:00+00:00",
                        "compensation": {"compensationTierSummary": "₹10L – ₹14L"},
                    },
                    {"id": "2", "title": "Hidden", "isListed": False, "jobUrl": "x"},
                ]
            }
        },
    )
    jobs = ats.AshbySource([WatchedCompany(name="Acme", ats="ashby", board="acme")]).fetch()

    assert [j.title for j in jobs] == ["Frontend Engineer"]
    assert jobs[0].location == "Bengaluru, Remote (India)"
    assert jobs[0].salary_text == "₹10L – ₹14L"


def test_one_bad_board_does_not_hide_the_others(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "boards/gone/jobs": RuntimeError("404 Not Found"),
            "boards/acme/jobs": {"jobs": [{"id": 1, "title": "SDE", "absolute_url": "u", "location": {}}]},
        },
    )
    companies = [
        WatchedCompany(name="Gone", ats="greenhouse", board="gone"),
        WatchedCompany(name="Acme", ats="greenhouse", board="acme"),
        WatchedCompany(name="Other ATS", ats="lever", board="ignored"),
    ]
    jobs = ats.GreenhouseSource(companies).fetch()
    assert [j.company for j in jobs] == ["Acme"]


def test_all_boards_failing_raises_so_the_run_is_marked_error(monkeypatch):
    _stub_json(monkeypatch, {"boards/": RuntimeError("down")})
    source = ats.GreenhouseSource([WatchedCompany(name="A", ats="greenhouse", board="a")])
    with pytest.raises(RuntimeError):
        source.fetch()


def test_load_companies_reads_watchlist(tmp_path):
    path = tmp_path / "companies.yaml"
    path.write_text("companies:\n  - {name: Acme, ats: lever, board: acme}\n", encoding="utf-8")
    assert ats.load_companies(str(path)) == [WatchedCompany(name="Acme", ats="lever", board="acme")]
    assert ats.load_companies(str(tmp_path / "missing.yaml")) == []


def test_remotive(monkeypatch):
    calls = _stub_json(
        monkeypatch,
        {
            "remotive.com": {
                "0-legal-notice": "...",
                "jobs": [
                    {
                        "id": 7,
                        "url": "https://remotive.com/remote-jobs/software-development/x-7",
                        "title": "Junior Python Developer",
                        "company_name": "Beta",
                        "candidate_required_location": "Worldwide",
                        "description": "<p>Python</p>",
                        "publication_date": "2026-09-30T13:15:26",
                        "job_type": "full_time",
                        "tags": ["python"],
                        "salary": "",
                    }
                ],
            }
        },
    )
    jobs = aggregators.RemotiveSource().fetch()
    assert jobs[0].url.startswith("https://remotive.com/")  # attribution link-back
    assert jobs[0].is_remote and jobs[0].official_source is False
    assert calls[0][1] == {"category": "software-dev"}


def test_remoteok_skips_legal_notice_element(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "remoteok.com": [
                {"last_updated": 1, "legal": "API Terms of Service: ..."},
                {
                    "id": "99",
                    "position": "React Developer",
                    "company": "Gamma",
                    "url": "https://remoteOK.com/remote-jobs/99",
                    "location": "",
                    "description": "<p>React</p>",
                    "date": "2026-10-02T12:53:01+00:00",
                    "tags": ["react"],
                    "salary_min": 0,
                    "salary_max": 90000,
                },
            ]
        },
    )
    jobs = aggregators.RemoteOKSource().fetch()
    assert len(jobs) == 1
    assert jobs[0].title == "React Developer"
    assert jobs[0].salary_min is None and jobs[0].salary_max == 90000.0
    assert jobs[0].salary_currency == "USD"


def test_weworkremotely_parses_rss_and_splits_company(monkeypatch):
    rss = """<?xml version="1.0"?><rss><channel>
      <item><title>Edfinity: Full Stack Engineer</title><region>Anywhere in the World</region>
      <category>Full-Stack Programming</category><description>&lt;p&gt;Python + React&lt;/p&gt;</description>
      <pubDate>Mon, 17 Aug 2026 19:21:19 +0000</pubDate>
      <link>https://weworkremotely.com/remote-jobs/edfinity-full-stack</link></item>
    </channel></rss>"""
    monkeypatch.setattr("app.core.jobsources.http.get_text", lambda url, params=None: rss)
    source = aggregators.WeWorkRemotelySource()
    source.FEEDS = ("https://weworkremotely.com/feed.rss",)
    jobs = source.fetch()
    assert jobs[0].company == "Edfinity"
    assert jobs[0].title == "Full Stack Engineer"
    assert jobs[0].location == "Anywhere in the World"
    assert jobs[0].description == "Python + React"
    assert jobs[0].posted_at is not None and jobs[0].posted_at.month == 8


def test_himalayas_uses_search_and_location_restrictions(monkeypatch):
    calls = _stub_json(
        monkeypatch,
        {
            "himalayas.app": {
                "jobs": [
                    {
                        "title": "Software Engineer",
                        "companyName": "Delta",
                        "locationRestrictions": ["India", "Singapore"],
                        "applicationLink": "https://himalayas.app/companies/delta/jobs/se",
                        "guid": "https://himalayas.app/companies/delta/jobs/se",
                        "pubDate": 1791019030,
                        "description": "<p>TypeScript</p>",
                        "seniority": ["Entry-level"],
                        "minSalary": None,
                        "maxSalary": None,
                    },
                    {"title": "Dev", "companyName": "Eps", "locationRestrictions": [], "guid": "g2"},
                ]
            }
        },
    )
    jobs = aggregators.HimalayasSource(["python developer"]).fetch()
    assert jobs[0].location == "India, Singapore"
    assert jobs[1].location == "Worldwide"
    assert calls[0][1]["q"] == "python developer" and calls[0][1]["seniority"] == "Entry-level"


def test_arbeitnow(monkeypatch):
    _stub_json(
        monkeypatch,
        {
            "arbeitnow.com": {
                "data": [
                    {
                        "slug": "dev-berlin-1",
                        "company_name": "Zeta GmbH",
                        "title": "Developer",
                        "description": "<p>Go</p>",
                        "remote": False,
                        "url": "https://www.arbeitnow.com/jobs/dev-berlin-1",
                        "tags": [],
                        "job_types": ["Full Time"],
                        "location": "Berlin",
                        "created_at": 1791028823,
                    }
                ]
            }
        },
    )
    jobs = aggregators.ArbeitnowSource().fetch()
    assert jobs[0].location == "Berlin" and jobs[0].is_remote is False


def test_adzuna_skips_itself_without_keys(monkeypatch):
    monkeypatch.setattr("app.core.jobsources.aggregators.settings.adzuna_app_id", "")
    assert aggregators.AdzunaSource().is_configured() is False


def test_adzuna_maps_results_when_configured(monkeypatch):
    monkeypatch.setattr("app.core.jobsources.aggregators.settings.adzuna_app_id", "id")
    monkeypatch.setattr("app.core.jobsources.aggregators.settings.adzuna_app_key", "key")
    _stub_json(
        monkeypatch,
        {
            "api.adzuna.com": {
                "results": [
                    {
                        "id": 123,
                        "title": "<strong>Python</strong> Developer",
                        "company": {"display_name": "Omega"},
                        "location": {"display_name": "Pune, Maharashtra"},
                        "redirect_url": "https://www.adzuna.in/land/ad/123",
                        "description": "Python developer role",
                        "created": "2026-10-01T10:00:00Z",
                        "salary_max": 600000,
                    }
                ]
            }
        },
    )
    jobs = aggregators.AdzunaSource(["python"]).fetch()
    assert jobs[0].title == "Python Developer"
    assert jobs[0].salary_currency == "INR"


def test_fingerprint_ignores_formatting_noise():
    assert job_fingerprint("Acme", "Software Engineer (Remote)") == job_fingerprint(
        "ACME", "software engineer"
    )
    assert job_fingerprint("Acme", "Backend Engineer") != job_fingerprint("Acme", "Frontend Engineer")


def test_html_to_text_and_parse_datetime_edge_cases():
    assert html_to_text(None) == ""
    assert html_to_text("<ul><li>a</li><li>b</li></ul>").splitlines() == ["- a", "- b"]
    assert parse_datetime(None) is None
    assert parse_datetime("not a date") is None
    millis = parse_datetime(1786469891368)  # epoch millis
    assert millis is not None and millis.year == 2026
    naive = parse_datetime("2026-10-01T00:00:00")
    assert naive is not None and naive.tzinfo is not None
