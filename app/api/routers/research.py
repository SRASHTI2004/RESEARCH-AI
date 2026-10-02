from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.research import ResearchRequest, ResearchResponse, ResearchSummary
from app.services.research_service import run_research
from app.repositories import research_repository as repo

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse, status_code=201)
def create_research(
    request: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchResponse:
    job = run_research(db, request.company, current_user.id)

    if job.status == "failed":
        raise HTTPException(status_code=502, detail=job.error or "Research pipeline failed")

    return ResearchResponse.model_validate(job)


@router.get("", response_model=list[ResearchSummary])
def list_research(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResearchSummary]:
    # Admins see every job; everyone else sees only their own.
    owner_filter = None if current_user.role == "admin" else current_user.id
    jobs = repo.list_jobs(db, owner_id=owner_filter)
    return [ResearchSummary.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=ResearchResponse)
def get_research(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchResponse:
    job = repo.get_job(db, job_id)

    # 404 (not 403) for someone else's job — doesn't confirm to a caller
    # that a given job ID even exists.
    is_owner = job is not None and job.owner_id == current_user.id
    if job is None or not (is_owner or current_user.role == "admin"):
        raise HTTPException(status_code=404, detail="Research job not found")

    return ResearchResponse.model_validate(job)
