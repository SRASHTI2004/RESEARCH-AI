from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.job import Job
from app.repositories import application_repository as repo
from app.repositories import job_repository
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate

# Default reminder when moving to a status, if none is set yet.
DEFAULT_FOLLOW_UP_DAYS = {"applied": 7, "referral_asked": 5, "interview": 3}


class JobNotFoundError(Exception):
    pass


def to_out(application: Application) -> ApplicationOut:
    out = ApplicationOut.model_validate(application)
    if application.job is not None:
        out.job_score = application.job.score
    return out


def _apply_status_defaults(application: Application, today: date) -> None:
    if application.status == "applied" and application.applied_on is None:
        application.applied_on = today
    days = DEFAULT_FOLLOW_UP_DAYS.get(application.status)
    if days is not None and application.follow_up_on is None:
        application.follow_up_on = today + timedelta(days=days)


def create(db: Session, owner_id: str, payload: ApplicationCreate, today: date | None = None) -> Application:
    """Idempotent for feed jobs: saving a job you already track returns the
    existing entry instead of a duplicate."""
    today = today or date.today()
    job: Job | None = None
    if payload.job_id:
        job = job_repository.get_job(db, payload.job_id)
        if job is None:
            raise JobNotFoundError(payload.job_id)
        existing = repo.get_for_job(db, owner_id, job.id)
        if existing is not None:
            return existing

    application = Application(
        owner_id=owner_id,
        job_id=job.id if job else None,
        title=(payload.title or (job.title if job else "")).strip(),
        company=(payload.company or (job.company if job else "")).strip(),
        url=payload.url or (job.url if job else ""),
        location=payload.location or (job.location if job else ""),
        status=payload.status,
        notes=payload.notes,
        follow_up_on=payload.follow_up_on,
    )
    _apply_status_defaults(application, today)
    return repo.save(db, application)


def update(
    db: Session, application: Application, payload: ApplicationUpdate, today: date | None = None
) -> Application:
    today = today or date.today()
    sent = payload.model_fields_set
    if "notes" in sent and payload.notes is not None:
        application.notes = payload.notes
    if "follow_up_on" in sent:
        application.follow_up_on = payload.follow_up_on
    if "applied_on" in sent:
        application.applied_on = payload.applied_on
    if "status" in sent and payload.status is not None and payload.status != application.status:
        application.status = payload.status
        # A new stage gets a fresh default reminder unless one was sent explicitly.
        if "follow_up_on" not in sent:
            application.follow_up_on = None
        _apply_status_defaults(application, today)
    return repo.save(db, application)
