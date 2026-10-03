import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TailoredResume(Base):
    """One tailored version of the master resume for one job. Lives only in
    the local database (git-ignored, blocked by the forbidden-files check)."""

    __tablename__ = "tailored_resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_tailored_resumes_owner_id_users"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL", name="fk_tailored_resumes_job_id_jobs"),
        nullable=True,
        index=True,
    )
    job_title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)

    content: Mapped[dict] = mapped_column(JSON, nullable=False)  # app.core.resume.Resume as a dict
    diff: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # [{"op", "text"}]
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    keywords_matched: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    keywords_missing: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    used_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
