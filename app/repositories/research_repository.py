from sqlalchemy import select
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


def get_job(db: Session, job_id: str) -> ResearchJob | None:
    return db.get(ResearchJob, job_id)


def list_jobs(db: Session, limit: int = 50, owner_id: str | None = None) -> list[ResearchJob]:
    """owner_id=None means "no filter" (admin, sees every job) — callers
    decide that, this function just applies whatever filter it's given."""
    stmt = select(ResearchJob).order_by(ResearchJob.created_at.desc()).limit(limit)
    if owner_id is not None:
        stmt = stmt.where(ResearchJob.owner_id == owner_id)
    return list(db.scalars(stmt))
