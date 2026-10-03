from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job, SourceRun

# Same rule as Job.score, in SQL: the LLM score when there is one.
effective_score = func.coalesce(Job.llm_score, Job.rule_score)


def get_job(db: Session, job_id: str) -> Job | None:
    return db.get(Job, job_id)


def get_by_fingerprint(db: Session, fingerprint: str) -> Job | None:
    return db.scalars(select(Job).where(Job.fingerprint == fingerprint)).first()


def add(db: Session, job: Job) -> Job:
    db.add(job)
    return job


def list_jobs(
    db: Session,
    *,
    include_filtered: bool = False,
    min_score: int | None = None,
    fresher_only: bool = False,
    source: str | None = None,
    query: str | None = None,
    seen_since: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Job], int]:
    stmt = select(Job)
    if not include_filtered:
        stmt = stmt.where(Job.passed_prefilter.is_(True))
    if min_score is not None:
        stmt = stmt.where(effective_score >= min_score)
    if fresher_only:
        stmt = stmt.where(Job.fresher_friendly.is_(True))
    if source:
        stmt = stmt.where(Job.source == source)
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(or_(func.lower(Job.title).like(like), func.lower(Job.company).like(like)))
    if seen_since is not None:
        stmt = stmt.where(Job.first_seen_at >= seen_since)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(effective_score.desc(), Job.first_seen_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt)), total


def all_jobs(db: Session) -> list[Job]:
    return list(db.scalars(select(Job)))


def record_source_run(db: Session, run: SourceRun) -> SourceRun:
    db.add(run)
    db.commit()
    return run


def last_successful_run(db: Session, source: str) -> SourceRun | None:
    stmt = (
        select(SourceRun)
        .where(SourceRun.source == source, SourceRun.status == "ok")
        .order_by(SourceRun.started_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def latest_runs(db: Session) -> list[SourceRun]:
    """Most recent run per source."""
    latest = (
        select(SourceRun.source, func.max(SourceRun.id).label("max_id")).group_by(SourceRun.source).subquery()
    )
    stmt = select(SourceRun).join(latest, SourceRun.id == latest.c.max_id).order_by(SourceRun.source)
    return list(db.scalars(stmt))
