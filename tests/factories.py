from datetime import UTC, datetime
from typing import Any

from app.core.jobsources.base import JobSource, NormalizedJob, job_fingerprint
from app.models.job import Job

GOOD_DESCRIPTION = (
    "We are hiring a junior engineer to build web apps with Python, FastAPI and React. "
    "You'll work with TypeScript on the frontend and SQL databases on the backend. "
    "0-1 years of experience is fine; freshers welcome. Mentorship, code review and a friendly team."
)


def make_posting(**overrides) -> NormalizedJob:
    data: dict[str, Any] = {
        "source": "greenhouse",
        "external_id": "acme:1",
        "title": "Software Engineer",
        "company": "Acme",
        "url": "https://boards.greenhouse.io/acme/jobs/1",
        "location": "Bengaluru, India",
        "is_remote": False,
        "description": GOOD_DESCRIPTION,
        "posted_at": datetime.now(UTC),
        "official_source": True,
    }
    data.update(overrides)
    return NormalizedJob(**data)


def make_job(**overrides) -> Job:
    data: dict[str, Any] = {
        "source": "greenhouse",
        "external_id": "acme:1",
        "official_source": True,
        "title": "Software Engineer",
        "company": "Acme",
        "location": "Bengaluru, India",
        "is_remote": False,
        "url": "https://boards.greenhouse.io/acme/jobs/1",
        "description": GOOD_DESCRIPTION,
        "employment_type": "",
        "tags": [],
        "salary_text": "",
        "salary_currency": "",
        "passed_prefilter": True,
        "prefilter_reason": "India",
        "rule_score": 50,
        "red_flags": [],
    }
    data.update(overrides)
    data.setdefault("fingerprint", job_fingerprint(data["company"], data["title"]))
    return Job(**data)


class FakeSource(JobSource):
    def __init__(
        self, name: str, postings: list[NormalizedJob] | None = None, error: Exception | None = None
    ):
        self.name = name
        self.postings = postings or []
        self.error = error
        self.calls = 0

    def fetch(self) -> list[NormalizedJob]:
        self.calls += 1
        if self.error:
            raise self.error
        return self.postings
