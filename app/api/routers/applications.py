from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.application import Application
from app.models.user import User
from app.repositories import application_repository as repo
from app.schemas.application import (
    ApplicationCreate,
    ApplicationList,
    ApplicationOut,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services import application_service as service

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_own_or_404(db: Session, application_id: str, user: User) -> Application:
    """Strictly owner-only (no admin override): the tracker holds personal
    notes. 404 rather than 403, same as research jobs."""
    application = repo.get(db, application_id)
    if application is None or application.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("", response_model=ApplicationList)
def list_applications(
    status: ApplicationStatus | None = None,
    q: str | None = Query(None, max_length=100),
    due: Literal["overdue", "today", "week"] | None = Query(None, description="Follow-ups due by…"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationList:
    today = date.today()
    due_by = {
        "overdue": today - timedelta(days=1),
        "today": today,
        "week": today + timedelta(days=7),
        None: None,
    }[due]
    items = repo.list_for_owner(db, user.id, status=status, query=q, follow_up_due_by=due_by)
    return ApplicationList(items=[service.to_out(a) for a in items], counts=repo.status_counts(db, user.id))


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ApplicationOut:
    try:
        application = service.create(db, user.id, payload)
    except service.JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return service.to_out(application)


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationOut:
    application = _get_own_or_404(db, application_id, user)
    return service.to_out(service.update(db, application, payload))


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    repo.delete(db, _get_own_or_404(db, application_id, user))
