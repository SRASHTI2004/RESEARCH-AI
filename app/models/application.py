import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.job import Job

# Ordered as a pipeline — the UI shows them in this order.
APPLICATION_STATUSES = ("saved", "applied", "referral_asked", "interview", "rejected", "offer")
# Statuses where a follow-up reminder still makes sense.
ACTIVE_STATUSES = ("saved", "applied", "referral_asked", "interview")


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Application(Base):
    """One user's tracking entry for a job. Per-user (row-level, like
    research jobs), unlike `jobs` which are shared."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("owner_id", "job_id", name="uq_applications_owner_job"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_applications_owner_id_users"),
        nullable=False,
        index=True,
    )
    # Nullable: you can also track a role found elsewhere (manual entry),
    # and a tracked job survives the posting being cleaned up.
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL", name="fk_applications_job_id_jobs"), nullable=True
    )

    # Copied from the job at save time so the entry stays readable on its own.
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="saved", index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    applied_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    follow_up_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    job: Mapped[Job | None] = relationship()
