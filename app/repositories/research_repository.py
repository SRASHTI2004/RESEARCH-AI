from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.research_job import ResearchJob, ResearchSource


def create_job(db: Session, company: str, owner_id: str | None = None) -> ResearchJob:
    job = ResearchJob(company=company, status="pending", owner_id=owner_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def save_result(db: Session, job: ResearchJob, result: dict) -> ResearchJob:
    """Persist the pipeline's final state onto an existing job row.

    Called whether the pipeline succeeded or failed — a failed run is still
    saved (with its error message) so it shows up in history instead of
    vanishing.
    """
    job.status = result["status"]
    job.error = result.get("error")
    job.research = result.get("research", "")
    job.analysis = result.get("analysis", "")
    job.report = result.get("report", "")
    job.final_report = result.get("final_report", "")
    job.sources = [
        ResearchSource(
            index=s["index"],
            title=s["title"],
            url=s["url"],
            snippet=s.get("snippet", ""),
        )
        for s in result.get("sources", [])
    ]

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def set_export_key(db: Session, job: ResearchJob, object_key: str) -> ResearchJob:
    job.export_object_key = object_key
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> ResearchJob | None:
    return db.get(ResearchJob, job_id)


def list_jobs(db: Session, limit: int = 50, owner_id: str | None = None) -> list[ResearchJob]:
    """owner_id=None means "no filter" (admin, sees every job) — callers
    decide that, this function just applies whatever filter it's given."""
    stmt = select(ResearchJob).order_by(ResearchJob.created_at.desc()).limit(limit)
    if owner_id is not None:
        stmt = stmt.where(ResearchJob.owner_id == owner_id)
    return list(db.scalars(stmt))


def latest_for_company(db: Session, company: str, owner_id: str) -> ResearchJob | None:
    """Most recent brief this user ran for `company` (case/whitespace-insensitive)
    — lets a job page reuse an existing brief instead of spending LLM quota again."""
    stmt = (
        select(ResearchJob)
        .where(
            ResearchJob.owner_id == owner_id,
            func.lower(func.trim(ResearchJob.company)) == company.strip().lower(),
        )
        .order_by(ResearchJob.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
