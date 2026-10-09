"""Public remote-job feeds. Each one's terms (checked 2026-10-03, see
docs/DECISIONS.md) ask for attribution + a link back to the original
listing — so `url` is always the listing on that site and the UI/digest
show "via <source>". Polling intervals follow each site's stated guidance.
"""

import logging
import time
from typing import Any

from defusedxml import ElementTree

from app.core.config import settings
from app.core.jobsources import http
from app.core.jobsources.base import JobSource, NormalizedJob
from app.core.jobsources.text import html_to_text, parse_datetime

logger = logging.getLogger(__name__)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "", 0) else None
    except (TypeError, ValueError):
        return None


class RemotiveSource(JobSource):
    """remotive.com/api/remote-jobs — terms: link back + credit Remotive, max ~4 requests/day."""

    name = "remotive"
    min_interval_hours = 8.0

    def fetch(self) -> list[NormalizedJob]:
        data = http.get_json("https://remotive.com/api/remote-jobs", params={"category": "software-dev"})
        return [
            NormalizedJob(
                source=self.name,
                external_id=str(item["id"]),
                title=item.get("title", "").strip(),
                company=item.get("company_name", "").strip(),
                url=item.get("url", ""),
                location=item.get("candidate_required_location", "") or "",
                is_remote=True,
                description=html_to_text(item.get("description")),
                posted_at=parse_datetime(item.get("publication_date")),
                employment_type=item.get("job_type", "") or "",
                tags=list(item.get("tags") or []),
                salary_text=item.get("salary", "") or "",
            )
            for item in data.get("jobs", [])
        ]


class RemoteOKSource(JobSource):
    """remoteok.com/api — terms: link back to the Remote OK URL and name Remote OK as the source.
    The first array element is the legal notice, not a job."""

    name = "remoteok"
    min_interval_hours = 6.0

    def fetch(self) -> list[NormalizedJob]:
        data = http.get_json("https://remoteok.com/api")
        jobs = []
        for item in data:
            if "id" not in item or "position" not in item:
                continue
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item["id"]),
                    title=item.get("position", "").strip(),
                    company=item.get("company", "").strip(),
                    url=item.get("url", ""),
                    location=item.get("location", "") or "",
                    is_remote=True,
                    description=html_to_text(item.get("description")),
                    posted_at=parse_datetime(item.get("date") or item.get("epoch")),
                    tags=list(item.get("tags") or []),
                    salary_min=_float_or_none(item.get("salary_min")),
                    salary_max=_float_or_none(item.get("salary_max")),
                    salary_currency="USD" if item.get("salary_max") else "",
                )
            )
        return jobs


class WeWorkRemotelySource(JobSource):
    """Public category RSS feeds (no JSON API is offered publicly). robots.txt allows them."""

    name = "weworkremotely"
    min_interval_hours = 6.0
    FEEDS: tuple[str, ...] = (
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    )

    def fetch(self) -> list[NormalizedJob]:
        jobs = []
        for feed_url in self.FEEDS:
            root = ElementTree.fromstring(http.get_text(feed_url))
            for item in root.iter("item"):
                raw_title = (item.findtext("title") or "").strip()
                # Titles are "Company: Role".
                company, _, title = raw_title.partition(": ")
                if not title:
                    company, title = "", raw_title
                link = (item.findtext("link") or item.findtext("guid") or "").strip()
                jobs.append(
                    NormalizedJob(
                        source=self.name,
                        external_id=link,
                        title=title.strip(),
                        company=company.strip(),
                        url=link,
                        location=(item.findtext("region") or "").strip(),
                        is_remote=True,
                        description=html_to_text(item.findtext("description")),
                        posted_at=parse_datetime(item.findtext("pubDate")),
                        tags=[(item.findtext("category") or "").strip()],
                    )
                )
        return jobs


class HimalayasSource(JobSource):
    """himalayas.app/jobs/api/search — terms: link back + credit Himalayas; data refreshes daily."""

    name = "himalayas"
    min_interval_hours = 20.0

    def __init__(self, queries: list[str] | None = None) -> None:
        self.queries = queries or ["software engineer", "developer"]

    def fetch(self) -> list[NormalizedJob]:
        jobs = []
        for query in self.queries:
            data = http.get_json(
                "https://himalayas.app/jobs/api/search",
                params={"q": query, "seniority": "Entry-level", "sort": "recent"},
            )
            for item in data.get("jobs", []):
                restrictions = item.get("locationRestrictions") or []
                url = item.get("applicationLink") or item.get("guid") or ""
                jobs.append(
                    NormalizedJob(
                        source=self.name,
                        external_id=item.get("guid") or url,
                        title=item.get("title", "").strip(),
                        company=item.get("companyName", "").strip(),
                        url=url,
                        location=", ".join(restrictions) if restrictions else "Worldwide",
                        is_remote=True,
                        description=html_to_text(item.get("description") or item.get("excerpt")),
                        posted_at=parse_datetime(item.get("pubDate")),
                        employment_type=item.get("employmentType", "") or "",
                        tags=list(item.get("seniority") or []),
                        salary_min=_float_or_none(item.get("minSalary")),
                        salary_max=_float_or_none(item.get("maxSalary")),
                        salary_currency=item.get("currency") or "",
                    )
                )
        return jobs


class ArbeitnowSource(JobSource):
    """arbeitnow.com/api/job-board-api — free public API; asks for a link back. Mostly EU roles."""

    name = "arbeitnow"
    min_interval_hours = 6.0

    def fetch(self) -> list[NormalizedJob]:
        data = http.get_json("https://www.arbeitnow.com/api/job-board-api")
        return [
            NormalizedJob(
                source=self.name,
                external_id=item.get("slug") or item.get("url", ""),
                title=item.get("title", "").strip(),
                company=item.get("company_name", "").strip(),
                url=item.get("url", ""),
                location=item.get("location", "") or "",
                is_remote=bool(item.get("remote")),
                description=html_to_text(item.get("description")),
                posted_at=parse_datetime(item.get("created_at")),
                employment_type=", ".join(item.get("job_types") or []),
                tags=list(item.get("tags") or []),
            )
            for item in data.get("data", [])
        ]


class AdzunaSource(JobSource):
    """api.adzuna.com — needs a free developer app_id/app_key; skipped when unset.
    Descriptions are short snippets by design of the API."""

    name = "adzuna"
    min_interval_hours = 12.0

    def __init__(self, queries: list[str] | None = None) -> None:
        self.queries = queries or ["software engineer", "developer"]

    def is_configured(self) -> bool:
        return bool(settings.adzuna_app_id and settings.adzuna_app_key)

    def fetch(self) -> list[NormalizedJob]:
        jobs = []
        places = [w.strip() for w in settings.adzuna_where.split(",")] or [""]
        first = True
        for query in self.queries:
            for place in places:
                if not first:
                    # Free tier allows ~25 requests/minute; stay well under it.
                    time.sleep(2.6)
                first = False
                params: dict[str, str | int] = {
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "what": query,
                    "results_per_page": 50,
                    "max_days_old": 7,
                    "content-type": "application/json",
                }
                if place:
                    params["where"] = place
                data = http.get_json(
                    f"https://api.adzuna.com/v1/api/jobs/{settings.adzuna_country}/search/1", params=params
                )
                for item in data.get("results", []):
                    # Adzuna fills in its own estimate when the employer gives no salary.
                    predicted = str(item.get("salary_is_predicted", "0")) == "1"
                    location = (item.get("location") or {}).get("display_name", "") or ""
                    description = html_to_text(item.get("description"))
                    jobs.append(
                        NormalizedJob(
                            source=self.name,
                            external_id=str(item.get("id")),
                            title=html_to_text(item.get("title")),
                            company=(item.get("company") or {}).get("display_name", "") or "",
                            url=item.get("redirect_url", ""),
                            location=location,
                            is_remote="remote" in f"{location} {description}".lower(),
                            description=description,
                            posted_at=parse_datetime(item.get("created")),
                            employment_type=item.get("contract_time", "") or "",
                            salary_min=None if predicted else _float_or_none(item.get("salary_min")),
                            salary_max=None if predicted else _float_or_none(item.get("salary_max")),
                            salary_currency="" if predicted or settings.adzuna_country != "in" else "INR",
                        )
                    )
        return jobs
