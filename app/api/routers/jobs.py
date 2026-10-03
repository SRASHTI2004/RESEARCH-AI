from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.job import Job
from app.models.user import User
from app.repositories import job_repository as repo
from app.schemas.job import JobDetail, JobList, JobSummary, SourceRunOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_or_404(db: Session, job_id: str) -> Job:
    job = repo.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=JobList)
def list_jobs(
    include_filtered: bool = False,
    min_score: int | None = Query(None, ge=0, le=100),
    source: str | None = None,
    q: str | None = Query(None, max_length=100),
    days: int | None = Query(None, ge=1, le=365, description="Only jobs first seen in the last N days"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> JobList:
    seen_since = datetime.now(UTC) - timedelta(days=days) if days else None
    jobs, total = repo.list_jobs(
        db,
        include_filtered=include_filtered,
        min_score=min_score,
        source=source,
        query=q,
        seen_since=seen_since,
        limit=limit,
        offset=offset,
    )
    return JobList(items=[JobSummary.model_validate(j) for j in jobs], total=total)


@router.get("/sources", response_model=list[SourceRunOut])
def source_status(
    db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> list[SourceRunOut]:
    return [SourceRunOut.model_validate(r) for r in repo.latest_runs(db)]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> JobDetail:
    return JobDetail.model_validate(get_job_or_404(db, job_id))
