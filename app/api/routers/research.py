from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.research import ResearchRequest, ResearchResponse, ResearchSummary
from app.services.research_service import run_research
from app.repositories import research_repository as repo

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse)
def create_research(request: ResearchRequest, db: Session = Depends(get_db)) -> ResearchResponse:
    job = run_research(db, request.company)

    if job.status == "failed":
        raise HTTPException(status_code=502, detail=job.error or "Research pipeline failed")

    return ResearchResponse.model_validate(job)


@router.get("", response_model=list[ResearchSummary])
def list_research(db: Session = Depends(get_db)) -> list[ResearchSummary]:
    jobs = repo.list_jobs(db)
    return [ResearchSummary.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=ResearchResponse)
def get_research(job_id: str, db: Session = Depends(get_db)) -> ResearchResponse:
    job = repo.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Research job not found")
    return ResearchResponse.model_validate(job)
