import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company: Mapped[str] = mapped_column(String(200), nullable=False)

    # Nullable so the column addition doesn't break any pre-existing rows;
    # every job created through the API always sets this (auth is required).
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # researching | analyzing | writing | done | failed (see app/pipeline/graph.py)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    research: Mapped[str] = mapped_column(Text, nullable=False, default="")
    analysis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    report: Mapped[str] = mapped_column(Text, nullable=False, default="")
    final_report: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    sources: Mapped[list["ResearchSource"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="ResearchSource.index",
    )


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False)

    index: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")

    job: Mapped["ResearchJob"] = relationship(back_populates="sources")
