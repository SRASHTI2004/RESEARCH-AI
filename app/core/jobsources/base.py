import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedJob:
    """One posting, in the single schema every source maps into."""

    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: str = ""
    is_remote: bool = False
    description: str = ""
    posted_at: datetime | None = None
    employment_type: str = ""
    tags: list[str] = field(default_factory=list)
    salary_text: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    # True for a company's own ATS board (Greenhouse/Lever/Ashby) — the
    # posting comes straight from the employer, not a re-post.
    official_source: bool = False

    @property
    def fingerprint(self) -> str:
        return job_fingerprint(self.company, self.title)


_NOISE = re.compile(r"\((?:m/f/d|f/m/d|m/w/d|w/m/d|all genders)\)|\bremote\b|\bhybrid\b", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _NON_ALNUM.sub(" ", _NOISE.sub(" ", text).lower()).strip()


def job_fingerprint(company: str, title: str) -> str:
    """Cross-source dedupe key: the same role at the same company, however
    each board formats it ("Software Engineer (Remote)" vs "Software
    Engineer"). Location is deliberately left out so a role re-posted on an
    aggregator collapses into the official listing."""
    key = f"{_normalize(company)}|{_normalize(title)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


class JobSource(ABC):
    name: str
    # Minimum hours between real fetches — respects each provider's stated
    # polling guidance (e.g. Remotive: max ~4 calls/day).
    min_interval_hours: float = 6.0

    def is_configured(self) -> bool:
        return True

    @abstractmethod
    def fetch(self) -> list[NormalizedJob]:
        """Return current postings. May raise; the ingest service isolates failures per source."""
