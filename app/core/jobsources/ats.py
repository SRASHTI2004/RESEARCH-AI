"""Official company job boards via their public, documented posting APIs:

- Greenhouse Job Board API: boards-api.greenhouse.io/v1/boards/{board}/jobs
- Lever Postings API:       api.lever.co/v0/postings/{board}
- Ashby Posting API:        api.ashbyhq.com/posting-api/job-board/{board}

All three are published by the ATS vendors specifically so companies'
postings can be displayed elsewhere; none need a key. Which companies to
query comes from config/companies.yaml.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.core.config import settings
from app.core.jobsources import http
from app.core.jobsources.base import JobSource, NormalizedJob
from app.core.jobsources.text import html_to_text, parse_datetime

logger = logging.getLogger(__name__)


class WatchedCompany(BaseModel):
    name: str
    ats: str  # greenhouse | lever | ashby
    board: str


def load_companies(path: str | None = None) -> list[WatchedCompany]:
    companies_path = Path(path or settings.companies_path)
    if not companies_path.exists():
        logger.warning("Company watchlist %s not found — ATS sources will return nothing", companies_path)
        return []
    data = yaml.safe_load(companies_path.read_text(encoding="utf-8")) or {}
    return [WatchedCompany.model_validate(entry) for entry in data.get("companies", [])]


def _is_remote_text(*values: str) -> bool:
    return any("remote" in (v or "").lower() for v in values)


class _ATSSource(JobSource):
    ats: str
    min_interval_hours = 6.0

    def __init__(self, companies: list[WatchedCompany] | None = None) -> None:
        self._companies = companies

    def companies(self) -> list[WatchedCompany]:
        all_companies = self._companies if self._companies is not None else load_companies()
        return [c for c in all_companies if c.ats == self.ats]

    def fetch(self) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        failures = 0
        watched = self.companies()
        for company in watched:
            # One bad/renamed board token mustn't hide every other company's jobs.
            try:
                jobs.extend(self.fetch_company(company))
            except Exception as exc:
                failures += 1
                logger.warning("%s board '%s' (%s) failed: %s", self.ats, company.board, company.name, exc)
        if watched and failures == len(watched):
            raise RuntimeError(f"all {failures} {self.ats} boards failed")
        return jobs

    def fetch_company(self, company: WatchedCompany) -> list[NormalizedJob]:
        raise NotImplementedError


class GreenhouseSource(_ATSSource):
    name = ats = "greenhouse"

    def fetch_company(self, company: WatchedCompany) -> list[NormalizedJob]:
        data = http.get_json(
            f"https://boards-api.greenhouse.io/v1/boards/{company.board}/jobs", params={"content": "true"}
        )
        jobs = []
        for item in data.get("jobs", []):
            location = (item.get("location") or {}).get("name", "") or ""
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=f"{company.board}:{item['id']}",
                    title=item.get("title", "").strip(),
                    company=company.name,
                    url=item.get("absolute_url", ""),
                    location=location,
                    is_remote=_is_remote_text(location),
                    description=html_to_text(item.get("content")),
                    posted_at=parse_datetime(item.get("first_published") or item.get("updated_at")),
                    official_source=True,
                )
            )
        return jobs


class LeverSource(_ATSSource):
    name = ats = "lever"

    def fetch_company(self, company: WatchedCompany) -> list[NormalizedJob]:
        data = http.get_json(f"https://api.lever.co/v0/postings/{company.board}", params={"mode": "json"})
        jobs = []
        for item in data:
            categories = item.get("categories") or {}
            location = categories.get("location", "") or ""
            sections = [item.get("descriptionPlain", "")]
            for section in item.get("lists") or []:
                sections.append(f"{section.get('text', '')}\n{html_to_text(section.get('content'))}")
            sections.append(item.get("additionalPlain", ""))
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=f"{company.board}:{item['id']}",
                    title=item.get("text", "").strip(),
                    company=company.name,
                    url=item.get("hostedUrl", ""),
                    location=location,
                    is_remote=item.get("workplaceType") == "remote" or _is_remote_text(location),
                    description="\n\n".join(s for s in sections if s).strip(),
                    posted_at=parse_datetime(item.get("createdAt")),
                    employment_type=categories.get("commitment", "") or "",
                    official_source=True,
                )
            )
        return jobs


class AshbySource(_ATSSource):
    name = ats = "ashby"

    def fetch_company(self, company: WatchedCompany) -> list[NormalizedJob]:
        data = http.get_json(
            f"https://api.ashbyhq.com/posting-api/job-board/{company.board}",
            params={"includeCompensation": "true"},
        )
        jobs = []
        for item in data.get("jobs", []):
            if item.get("isListed") is False:
                continue
            locations = [item.get("location", "")] + [
                s.get("location", "") for s in item.get("secondaryLocations") or []
            ]
            location = ", ".join(loc for loc in locations if loc)
            compensation: dict[str, Any] = item.get("compensation") or {}
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=f"{company.board}:{item['id']}",
                    title=item.get("title", "").strip(),
                    company=company.name,
                    url=item.get("jobUrl", ""),
                    location=location,
                    is_remote=bool(item.get("isRemote")) or _is_remote_text(location),
                    description=item.get("descriptionPlain") or html_to_text(item.get("descriptionHtml")),
                    posted_at=parse_datetime(item.get("publishedAt")),
                    employment_type=item.get("employmentType", "") or "",
                    salary_text=compensation.get("compensationTierSummary", "") or "",
                    official_source=True,
                )
            )
        return jobs
