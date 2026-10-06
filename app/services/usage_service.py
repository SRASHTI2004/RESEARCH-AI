"""Site-wide daily budget for LLM-heavy actions.

A public demo shares one free-tier LLM quota between every visitor, so
briefs and resume tailoring are capped per rolling 24 hours. Counting rows
already in the database keeps this stateless: no counter to reset, and it
survives restarts (Render's free tier restarts the app often).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.research_job import ResearchJob
from app.models.tailored_resume import TailoredResume


class DailyLimitReachedError(Exception):
    pass


def actions_last_24h(db: Session, now: datetime | None = None) -> int:
    since = (now or datetime.now(UTC)) - timedelta(hours=24)
    briefs = (
        db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.created_at >= since)) or 0
    )
    tailored = (
        db.scalar(
            select(func.count())
            .select_from(TailoredResume)
            .where(TailoredResume.created_at >= since, TailoredResume.used_llm.is_(True))
        )
        or 0
    )
    return briefs + tailored


def remaining(db: Session) -> int | None:
    """Actions left today, or None when there is no cap."""
    limit = settings.llm_daily_action_limit
    if limit <= 0:
        return None
    return max(0, limit - actions_last_24h(db))


def ensure_budget(db: Session) -> None:
    left = remaining(db)
    if left is not None and left <= 0:
        raise DailyLimitReachedError(
            f"This demo allows {settings.llm_daily_action_limit} AI actions per day across all visitors "
            "(free-tier LLM quota) and today's are used up. Pre-generated briefs are still available; "
            "please try again tomorrow."
        )
