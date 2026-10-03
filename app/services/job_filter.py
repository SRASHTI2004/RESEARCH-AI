"""Cheap rule-based pre-filter + ranking. Runs on every new job so the
LLM (rate-limited, free tier) only ever sees the ~30 most promising ones.

Biased towards *inclusion*: a false reject means a job is silently lost,
while a false accept just costs one slot the LLM scorer will mark down.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.jobsources.text import ensure_utc
from app.core.profile import Profile

SENIOR_TITLE = re.compile(
    r"\b(senior|sr\.?|lead|principal|staff|manager|director|head|architect|vp|vice president|chief|"
    r"distinguished|iii|iv)\b",
    re.IGNORECASE,
)
# Level 2+ ladders: "SDE 2", "Software Engineer II", "Engineer 3". Fresher roles are level 1 / unlevelled.
LEVELLED_TITLE = re.compile(r"\b(?:engineer|developer|sde|swe)[\s-]*(?:ii|iii|iv|v|[2-9])\b", re.IGNORECASE)

# "5+ years of experience", "3-5 yrs experience", "4–5 years building production apps"
_YEARS = re.compile(
    r"(?P<n>\d{1,2})\s*(?P<plus>\+)?\s*(?:(?P<range>-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b"
    r"(?P<after>[^.\n]{0,60})",
    re.IGNORECASE,
)
_EXPERIENCE_WORD = re.compile(r"experien|exp\b", re.IGNORECASE)
_NOT_A_REQUIREMENT = re.compile(r"\b(?:ago|old|warranty|anniversary|history)\b", re.IGNORECASE)

JUNIOR_SIGNALS = re.compile(
    r"\b(junior|jr\.?|fresher|freshers|entry[- ]level|graduate|new grad|intern|internship|trainee|"
    r"associate software|sde[- ]?(?:1|i)\b|engineer i\b|0\s*-\s*[12]\s*(?:years|yrs)|campus)",
    re.IGNORECASE,
)

INDIA_PLACES = (
    "india",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "pune",
    "chennai",
    "mumbai",
    "delhi",
    "ncr",
    "gurgaon",
    "gurugram",
    "noida",
    "kolkata",
    "ahmedabad",
    "kochi",
    "jaipur",
    "chandigarh",
    "indore",
    "coimbatore",
    "trivandrum",
    "thiruvananthapuram",
    "mohali",
    "nagpur",
    "bhubaneswar",
)

GLOBAL_REMOTE = ("anywhere", "worldwide", "global", "world", "apac", "asia", "asia-pacific")
_REMOTE_WORDS = re.compile(r"\b(?:fully\s+)?remote(?:\s+first)?\b|\bwork from home\b|\bwfh\b", re.IGNORECASE)


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text) is not None


def _has_any(text: str, words: tuple[str, ...] | list[str]) -> bool:
    return any(_has_word(text, w.lower()) for w in words)


def min_years_required(description: str) -> int | None:
    """Smallest "N years ... experience" requirement in the text, or None.
    Smallest, because postings often list a low hard requirement plus
    higher "nice to have" numbers."""
    found = []
    for m in _YEARS.finditer(description):
        after = m.group("after")
        if _NOT_A_REQUIREMENT.search(after):
            continue
        # "N+ years" and "N-M years" are requirement phrasing even without
        # the word "experience" ("3+ years of professional development").
        if _EXPERIENCE_WORD.search(after) or m.group("plus") or m.group("range"):
            found.append(int(m.group("n")))
    return min(found) if found else None


@dataclass
class LocationVerdict:
    ok: bool
    reason: str
    points: int


def evaluate_location(location: str, is_remote: bool, profile: Profile) -> LocationVerdict:
    prefs = profile.locations
    loc = location.lower()
    remote = is_remote or "remote" in loc

    cities = [c.lower() for c in prefs.preferred_cities if c.strip()]
    if cities and _has_any(loc, cities):
        return LocationVerdict(True, "preferred city", 20)

    if _has_any(loc, INDIA_PLACES):
        if remote or prefs.accept_any_india_city or not cities:
            return LocationVerdict(True, "India", 15)
        return LocationVerdict(False, "onsite in India but outside preferred cities", 0)

    if not remote:
        return LocationVerdict(False, f"onsite outside India ({location or 'unknown'})", 0)
    if not prefs.remote_ok:
        return LocationVerdict(False, "remote roles disabled in profile", 0)
    if not prefs.open_to_global_remote:
        return LocationVerdict(False, "remote but not open to India", 0)

    # Whatever remains after "remote" is the region the role is limited to
    # ("Remote (US)", "Foster City, CA", "Pakistan"); nothing left = anywhere.
    if not _REMOTE_WORDS.sub(" ", loc).strip(" ,-/()|;:") or _has_any(loc, GLOBAL_REMOTE):
        return LocationVerdict(True, "remote (worldwide)", 15)
    return LocationVerdict(False, f"remote but restricted to: {location}", 0)


@dataclass
class FilterResult:
    passed: bool
    reason: str
    rule_score: int


def evaluate(
    *,
    title: str,
    description: str,
    location: str,
    is_remote: bool,
    tags: list[str],
    official_source: bool,
    posted_at: datetime | None,
    profile: Profile,
    now: datetime | None = None,
) -> FilterResult:
    title_l = title.lower()

    senior = SENIOR_TITLE.search(title)
    if senior:
        return FilterResult(False, f"seniority keyword in title ('{senior.group(0)}')", 0)
    levelled = LEVELLED_TITLE.search(title)
    if levelled:
        return FilterResult(False, f"mid-level title ('{levelled.group(0)}')", 0)
    if not _has_any(title_l, profile.title_include_keywords):
        return FilterResult(False, "title is not a software/dev role", 0)
    excluded = next((w for w in profile.title_exclude_keywords if _has_word(title_l, w.lower())), None)
    if excluded:
        return FilterResult(False, f"title contains excluded keyword '{excluded}'", 0)

    years = min_years_required(description)
    if years is not None and years > profile.max_years_experience:
        return FilterResult(False, f"asks for {years}+ years of experience", 0)

    where = evaluate_location(location, is_remote, profile)
    if not where.ok:
        return FilterResult(False, where.reason, 0)

    # --- passed: compute a rough 0-100 rank for picking the LLM's top N ---
    haystack = f"{title}\n{description}\n{' '.join(tags)}".lower()
    stack = sum(8 for s in profile.primary_skills if _has_word(haystack, s.lower()))
    stack += sum(4 for s in profile.secondary_skills if _has_word(haystack, s.lower()))
    score = min(stack, 40)

    if JUNIOR_SIGNALS.search(title):
        score += 25
    elif JUNIOR_SIGNALS.search(description):
        score += 15

    score += where.points
    if official_source:
        score += 5
    posted = ensure_utc(posted_at)
    if posted is not None:
        age_days = ((now or datetime.now(UTC)) - posted).days
        score += 10 if age_days <= 3 else 5 if age_days <= 7 else 0

    return FilterResult(True, where.reason, min(score, 100))
