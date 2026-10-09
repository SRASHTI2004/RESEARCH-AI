"""The job seeker's profile (config/profile.yaml) — what the filter, scorer,
referral helper and resume tailor all match jobs against.

profile.yaml holds personal data, so it's git-ignored; the committed
config/profile.example.yaml is used as a fallback (with a warning) so the
app still runs on a fresh clone.
"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

EXAMPLE_PROFILE_PATH = "config/profile.example.yaml"

DEFAULT_TITLE_INCLUDE = [
    "engineer",
    "developer",
    "programmer",
    "sde",
    "software",
    "frontend",
    "front-end",
    "front end",
    "backend",
    "back-end",
    "back end",
    "full stack",
    "full-stack",
    "fullstack",
    "web",
    "python",
    "react",
]

DEFAULT_TITLE_EXCLUDE = [
    "sales",
    "marketing",
    "recruiter",
    "talent",
    "account executive",
    "customer success",
    "support",
    "mechanical",
    "electrical",
    "hardware",
    "civil",
    "finance",
    "legal",
    "writer",
    "designer",
]


class LocationPrefs(BaseModel):
    preferred_cities: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=lambda: ["India"])
    # Onsite/hybrid roles anywhere in India, not just preferred_cities.
    accept_any_india_city: bool = True
    remote_ok: bool = True
    open_to_global_remote: bool = True


class Profile(BaseModel):
    name: str = ""
    email: str = ""
    college: str = ""
    degree: str = ""
    graduation_year: int | None = None
    headline: str = "Fresher full-stack developer"
    summary: str = ""
    experience_level: str = "fresher"
    max_years_experience: int = 2
    # Postings older than this are dropped: old listings are often no longer hiring. 0 = keep all.
    max_posting_age_days: int = 45

    target_roles: list[str] = Field(default_factory=lambda: ["Software Engineer", "Full Stack Developer"])
    primary_skills: list[str] = Field(default_factory=list)
    secondary_skills: list[str] = Field(default_factory=list)

    locations: LocationPrefs = Field(default_factory=LocationPrefs)

    title_include_keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_TITLE_INCLUDE))
    title_exclude_keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_TITLE_EXCLUDE))

    # Free-text queries for search-style sources (Himalayas, Adzuna).
    search_queries: list[str] = Field(default_factory=lambda: ["software engineer", "developer"])

    links: dict[str, str] = Field(default_factory=dict)

    @property
    def all_skills(self) -> list[str]:
        return [*self.primary_skills, *self.secondary_skills]


def load_profile(path: str | None = None) -> Profile:
    profile_path = Path(path or settings.profile_path)
    if not profile_path.exists():
        logger.warning(
            "Profile file %s not found — using %s. Copy it to %s and fill in your details.",
            profile_path,
            EXAMPLE_PROFILE_PATH,
            settings.profile_path,
        )
        profile_path = Path(EXAMPLE_PROFILE_PATH)
        if not profile_path.exists():
            return Profile()

    data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    return Profile.model_validate(data)
