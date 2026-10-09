"""LLM scoring of the rule-ranked top N jobs against the profile.

Free-tier friendly by construction: only `SCORING_MAX_JOBS` jobs per run,
`SCORING_BATCH_SIZE` jobs per LLM call (30 jobs = 6 calls), and a pause
between calls. Unscored jobs (LLM down / rate-limited) simply stay
unscored and are retried on the next run.
"""

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import llm
from app.core.config import settings
from app.core.profile import Profile
from app.models.job import Job

logger = logging.getLogger(__name__)

DESCRIPTION_CHARS = 1000
# Stop early rather than burn the whole quota once providers are clearly down.
MAX_CONSECUTIVE_FAILURES = 2

# Indirection so tests can skip real sleeping.
_sleep: Callable[[float], None] = time.sleep


@dataclass
class ScoringSummary:
    candidates: int = 0
    scored: int = 0
    failed_batches: int = 0


def select_for_scoring(db: Session, limit: int, max_age_days: int = 14) -> list[Job]:
    since = datetime.now(UTC) - timedelta(days=max_age_days)
    stmt = (
        select(Job)
        .where(Job.passed_prefilter.is_(True), Job.llm_score.is_(None), Job.first_seen_at >= since)
        .order_by(Job.rule_score.desc(), Job.first_seen_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


_DECISIVE_LINE = re.compile(
    r"eligib|requir|qualif|must|experience|years?|yrs|graduat|batch|degree|cgpa|intern|fresher|"
    r"you have|you'll need|we're looking|looking for|skills|stack|location|based in|relocat|visa|onsite|remote",
    re.IGNORECASE,
)
INTRO_CHARS = 250


def excerpt(description: str, limit: int = DESCRIPTION_CHARS) -> str:
    """The first ~250 chars (what the role is) plus the lines that decide
    fit — requirements, years, graduation batch, location — rather than a
    blind prefix. Found in live testing: a "2027 graduates only" line at
    char 1,270 was cut off by a plain prefix, and the LLM scored an
    ineligible internship 60/100."""
    if len(description) <= limit:
        return description
    intro = description[:INTRO_CHARS]
    picked: list[str] = []
    budget = limit - len(intro) - 5
    for line in description[INTRO_CHARS:].splitlines():
        line = line.strip()
        if not line or not _DECISIVE_LINE.search(line):
            continue
        if len(line) + 1 > budget:
            continue
        picked.append(line)
        budget -= len(line) + 1
    return intro + " […]\n" + "\n".join(picked)


def _profile_block(profile: Profile) -> str:
    locs = profile.locations
    where = ", ".join(locs.preferred_cities) or "anywhere in India"
    return (
        f"Headline: {profile.headline}\n"
        f"Summary: {profile.summary.strip()}\n"
        f"Experience level: {profile.experience_level} (max {profile.max_years_experience} years acceptable)\n"
        f"Education: {profile.degree or 'not stated'}, graduation year {profile.graduation_year or 'not stated'}"
        f"{' (already graduated, not a current student)' if profile.graduation_year else ''}\n"
        f"Target roles: {', '.join(profile.target_roles)}\n"
        f"Primary skills: {', '.join(profile.primary_skills)}\n"
        f"Secondary skills: {', '.join(profile.secondary_skills)}\n"
        f"Location: prefers {where}"
        f"{'; also happy to relocate anywhere in India (do not penalise other Indian cities)' if locs.accept_any_india_city else ''}"
        f"; remote OK: {locs.remote_ok}; open to global remote: {locs.open_to_global_remote}"
    )


def build_prompt(profile: Profile, batch: list[tuple[str, Job]]) -> str:
    jobs_text = "\n\n".join(
        f"[{key}] {job.title} at {job.company}\n"
        f"Location: {job.location or 'not stated'} | Remote: {job.is_remote}\n"
        f"Description: {excerpt(job.description)}"
        for key, job in batch
    )
    return f"""You are helping a job seeker triage postings. Score how well each job fits THIS candidate.

CANDIDATE
{_profile_block(profile)}

JOBS
{jobs_text}

For each job return:
- "id": the job key in brackets (e.g. "J1")
- "score": integer 0-100 — overall fit (skills overlap, seniority fit for a fresher, location fit). 80+ = strong match, 50-79 = worth applying, below 40 = poor fit. If the posting states a hard requirement the candidate clearly does not meet (more years of experience, a specific graduation batch, current university enrollment, a degree or location restriction), score below 30. Hourly gig or contract work (e.g. AI training or data annotation) and roles aimed at clearly senior engineers score below 40.
- "reason": one sentence (max 25 words) naming the main match or mismatch. Use only facts from the posting and the candidate profile above.
- "fresher_friendly": true only if a fresher with an internship could realistically be hired (no hard multi-year experience requirement, not a senior/lead scope).

Respond with ONLY a JSON array, no prose, e.g. [{{"id": "J1", "score": 72, "reason": "...", "fresher_friendly": true}}]"""


def parse_scores(raw: str) -> list[dict]:
    """Tolerates code fences or chatter around the JSON array."""
    text = re.sub(r"```(?:json)?", "", raw)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("no JSON array in LLM response")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("LLM response is not a JSON array")
    return [d for d in data if isinstance(d, dict)]


def _apply(batch: list[tuple[str, Job]], entries: list[dict]) -> int:
    by_key = dict(batch)
    now = datetime.now(UTC)
    applied = 0
    for entry in entries:
        job = by_key.get(str(entry.get("id", "")).strip("[] "))
        if job is None:
            continue
        try:
            score = int(entry["score"])
        except (KeyError, TypeError, ValueError):
            continue
        job.llm_score = max(0, min(100, score))
        job.llm_reason = str(entry.get("reason", "")).strip()[:500]
        job.fresher_friendly = bool(entry.get("fresher_friendly"))
        job.scored_at = now
        applied += 1
    return applied


def score_jobs(db: Session, profile: Profile, jobs: list[Job]) -> ScoringSummary:
    summary = ScoringSummary(candidates=len(jobs))
    size = max(1, settings.scoring_batch_size)
    batches = [jobs[i : i + size] for i in range(0, len(jobs), size)]
    consecutive_failures = 0

    for index, chunk in enumerate(batches):
        if index > 0:
            _sleep(settings.scoring_min_interval_seconds)
        keyed = [(f"J{i + 1}", job) for i, job in enumerate(chunk)]
        try:
            raw = llm.invoke_llm(build_prompt(profile, keyed), temperature=0.1, stage="scoring")
            summary.scored += _apply(keyed, parse_scores(raw))
            db.commit()
            consecutive_failures = 0
        except (llm.LLMError, ValueError) as exc:
            summary.failed_batches += 1
            consecutive_failures += 1
            logger.warning("Scoring batch %d/%d failed: %s", index + 1, len(batches), exc)
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.warning("Stopping scoring early after %d consecutive failures", consecutive_failures)
                break

    logger.info(
        "Scoring: %d/%d jobs scored, %d failed batches",
        summary.scored,
        summary.candidates,
        summary.failed_batches,
    )
    return summary


def run_scoring(db: Session, profile: Profile, limit: int | None = None) -> ScoringSummary:
    return score_jobs(db, profile, select_for_scoring(db, limit or settings.scoring_max_jobs))
