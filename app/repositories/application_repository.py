from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.application import ACTIVE_STATUSES, Application


def get(db: Session, application_id: str) -> Application | None:
    return db.get(Application, application_id)


def get_for_job(db: Session, owner_id: str, job_id: str) -> Application | None:
    stmt = select(Application).where(Application.owner_id == owner_id, Application.job_id == job_id)
    return db.scalars(stmt).first()


def save(db: Session, application: Application) -> Application:
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def delete(db: Session, application: Application) -> None:
    db.delete(application)
    db.commit()


def list_for_owner(
    db: Session,
    owner_id: str,
    *,
    status: str | None = None,
    query: str | None = None,
    follow_up_due_by: date | None = None,
) -> list[Application]:
    stmt = select(Application).where(Application.owner_id == owner_id)
    if status:
        stmt = stmt.where(Application.status == status)
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Application.title).like(like),
                func.lower(Application.company).like(like),
                func.lower(Application.notes).like(like),
            )
        )
    if follow_up_due_by is not None:
        stmt = stmt.where(
            Application.follow_up_on.is_not(None),
            Application.follow_up_on <= follow_up_due_by,
            Application.status.in_(ACTIVE_STATUSES),
        )
    stmt = stmt.order_by(
        Application.follow_up_on.is_(None), Application.follow_up_on, Application.updated_at.desc()
    )
    return list(db.scalars(stmt))


def status_counts(db: Session, owner_id: str) -> dict[str, int]:
    stmt = (
        select(Application.status, func.count())
        .where(Application.owner_id == owner_id)
        .group_by(Application.status)
    )
    return {status: count for status, count in db.execute(stmt).tuples()}


def due_follow_ups(db: Session, today: date) -> list[Application]:
    """Every user's active applications whose follow-up date has arrived —
    for the digest, which goes to the single person who owns this install."""
    stmt = (
        select(Application)
        .where(
            Application.follow_up_on.is_not(None),
            Application.follow_up_on <= today,
            Application.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Application.follow_up_on)
    )
    return list(db.scalars(stmt))
