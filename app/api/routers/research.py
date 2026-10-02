from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import storage
from app.core.db import get_db
from app.core.rate_limit import limiter
from app.models.research_job import ResearchJob
from app.models.user import User
from app.repositories import research_repository as repo
from app.schemas.research import ResearchRequest, ResearchResponse, ResearchSummary
from app.services.research_service import enqueue_research

router = APIRouter(prefix="/research", tags=["research"])


def _get_visible_job_or_404(db: Session, job_id: str, current_user: User) -> ResearchJob:
    """A job is visible if the caller owns it or is an admin. 404 (not 403)
    for anything else — doesn't confirm to a caller that a given job ID
    even exists."""
    job = repo.get_job(db, job_id)
    is_owner = job is not None and job.owner_id == current_user.id
    if job is None or not (is_owner or current_user.role == "admin"):
        raise HTTPException(status_code=404, detail="Research job not found")
    return job


@router.post("", response_model=ResearchResponse, status_code=202)
@limiter.limit("10/minute")
def create_research(
    request: Request,
    payload: ResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResearchResponse:
    """Accepts the job and returns immediately — poll GET /research/{id}
    for progress (status moves researching -> analyzing -> writing -> done,
    or failed with an error message). Under the eager-mode dev fallback the
    job may already be finished by the time this responds; that's still a
    valid 202 "accepted" response, just a fast one."""
    job = enqueue_research(db, payload.company, current_user.id)
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
    job = _get_visible_job_or_404(db, job_id, current_user)
    return ResearchResponse.model_validate(job)


@router.get("/{job_id}/export")
def get_research_export(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Returns a short-lived presigned download URL for the object-storage
    copy of this job's final report (Phase 9 — optional; the frontend's
    client-side Markdown/PDF export works regardless of whether this is
    available)."""
    job = _get_visible_job_or_404(db, job_id, current_user)

    if not job.has_export or job.export_object_key is None:
        raise HTTPException(status_code=404, detail="No export available for this job")

    url = storage.get_download_url(job.export_object_key)
    if url is None:
        raise HTTPException(status_code=503, detail="Object storage is currently unavailable")

    return {"url": url}
