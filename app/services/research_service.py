from sqlalchemy.orm import Session

from app.models.research_job import ResearchJob
from app.repositories import research_repository as repo
from app.worker.tasks import run_research_job


def enqueue_research(db: Session, company: str, owner_id: str) -> ResearchJob:
    """Create the job row and hand it to the worker.

    Under the default eager Celery config (no Redis needed)
    `.delay()` actually runs the task synchronously in-process, so by the
    time this returns the job may already be done/failed. That's fine —
    the API contract (202 + poll GET /research/{id}) is correct either way;
    a real Redis-backed worker just means this returns before the job
    finishes, with the client polling to see it progress.
    """
    job = repo.create_job(db, company, owner_id=owner_id)
    run_research_job.delay(job.id, company)
    db.refresh(job)
    return job
