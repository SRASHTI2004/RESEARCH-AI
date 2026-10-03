from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routers.jobs import get_job_or_404
from app.core.db import get_db
from app.core.rate_limit import limiter
from app.core.resume import MasterResumeMissingError, Resume, load_master_resume
from app.models.tailored_resume import TailoredResume
from app.models.user import User
from app.schemas.resume import MasterResumeStatus, TailoredResumeOut, TailoredResumeSummary
from app.services import resume_export, resume_tailor

router = APIRouter(tags=["resume"])


def _load_master_or_409() -> Resume:
    try:
        return load_master_resume()
    except MasterResumeMissingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _own_or_404(db: Session, resume_id: str, user: User) -> TailoredResume:
    """Owner-only, like the tracker: resumes are personal."""
    item = db.get(TailoredResume, resume_id)
    if item is None or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    return item


@router.get("/resume/master", response_model=MasterResumeStatus)
def master_status(_user: User = Depends(get_current_user)) -> MasterResumeStatus:
    try:
        master = load_master_resume()
    except MasterResumeMissingError as exc:
        return MasterResumeStatus(exists=False, message=str(exc))
    return MasterResumeStatus(
        exists=True,
        message="",
        name=master.contact.name,
        experience=len(master.experience),
        projects=len(master.projects),
        skills=sum(len(g.items) for g in master.skills),
    )


@router.post("/jobs/{job_id}/tailored-resumes", response_model=TailoredResumeOut, status_code=201)
@limiter.limit("10/minute")
def create_tailored_resume(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TailoredResumeOut:
    """Synchronous (one LLM call, ~5-15 s). Reorders + rewords your real
    content for this job; never adds anything — see app/services/resume_tailor.py."""
    job = get_job_or_404(db, job_id)
    master = _load_master_or_409()
    result = resume_tailor.tailor(master, job)
    item = TailoredResume(
        owner_id=user.id,
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        content=result.resume.model_dump(),
        diff=[asdict(d) for d in result.diff],
        warnings=result.warnings,
        keywords_matched=result.keywords_matched,
        keywords_missing=result.keywords_missing,
        used_llm=result.used_llm,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return TailoredResumeOut.model_validate(item)


@router.get("/jobs/{job_id}/tailored-resumes", response_model=list[TailoredResumeSummary])
def list_tailored_resumes(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TailoredResumeSummary]:
    stmt = (
        select(TailoredResume)
        .where(TailoredResume.job_id == job_id, TailoredResume.owner_id == user.id)
        .order_by(TailoredResume.created_at.desc())
    )
    return [TailoredResumeSummary.model_validate(r) for r in db.scalars(stmt)]


@router.get("/tailored-resumes/{resume_id}", response_model=TailoredResumeOut)
def get_tailored_resume(
    resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TailoredResumeOut:
    return TailoredResumeOut.model_validate(_own_or_404(db, resume_id, user))


@router.get("/tailored-resumes/{resume_id}/export")
def export_tailored_resume(
    resume_id: str,
    format: Literal["pdf", "docx"] = "pdf",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    item = _own_or_404(db, resume_id, user)
    resume = Resume.model_validate(item.content)
    if format == "docx":
        body = resume_export.to_docx(resume)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        body = resume_export.to_pdf(resume)
        media = "application/pdf"
    filename = resume_export.export_filename(resume, item.company, format)
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )


@router.delete("/tailored-resumes/{resume_id}", status_code=204)
def delete_tailored_resume(
    resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    db.delete(_own_or_404(db, resume_id, user))
    db.commit()
