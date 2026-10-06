from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_llm_budget
from app.core.db import get_db
from app.core.profile import load_profile
from app.core.rate_limit import limiter
from app.models.job import Job
from app.models.user import User
from app.repositories import job_repository as repo
from app.repositories import research_repository
from app.schemas.job import JobDetail, JobList, JobSummary, ReferralKitOut, SourceRunOut
from app.schemas.research import ResearchResponse, ResearchSummary
from app.services.referral_service import build_referral_kit
from app.services.research_service import enqueue_research

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
    fresher_only: bool = False,
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
        fresher_only=fresher_only,
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


@router.get("/{job_id}/referral", response_model=ReferralKitOut)
def referral_kit(
    job_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> ReferralKitOut:
    """Search strings, a checklist and message drafts for asking for a
    referral. Generated from templates + your profile; nothing is sent."""
    kit = build_referral_kit(get_job_or_404(db, job_id), load_profile())
    return ReferralKitOut.model_validate(kit)


@router.get("/{job_id}/brief", response_model=ResearchSummary | None)
def latest_company_brief(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ResearchSummary | None:
    """Your latest Company Research Brief for this job's company, or null."""
    job = get_job_or_404(db, job_id)
    brief = research_repository.latest_for_company(db, job.company, user.id)
    return ResearchSummary.model_validate(brief) if brief else None


@router.post(
    "/{job_id}/brief",
    response_model=ResearchResponse,
    status_code=202,
    dependencies=[Depends(require_llm_budget)],
)
@limiter.limit("10/minute")
def generate_company_brief(
    request: Request, job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ResearchResponse:
    """Runs the existing research pipeline for this job's company — same
    path as POST /research, so it shows up in brief history too."""
    job = get_job_or_404(db, job_id)
    return ResearchResponse.model_validate(enqueue_research(db, job.company, user.id))
