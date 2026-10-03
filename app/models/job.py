import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Job(Base):
    """One deduplicated posting. Jobs are shared (not per-user): they come
    from public boards and are scored against the single profile file."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Cross-source dedupe key — see app/core/jobsources/base.py:job_fingerprint.
    fingerprint: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    official_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    employment_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    salary_text: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Rule-based pre-filter (cheap, runs on every new job).
    passed_prefilter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    prefilter_reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    rule_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Genuineness signals — heuristics, shown as "check this", never a verdict.
    red_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class SourceRun(Base):
    """One fetch attempt for one source — drives per-source polling
    intervals and the "last fetched" status shown in the UI."""

    __tablename__ = "source_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # ok | error | skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
