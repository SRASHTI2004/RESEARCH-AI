from sqlalchemy.orm import Session

from app.models.research_job import ResearchJob
from app.pipeline.graph import run_research as _run_research
from app.repositories import research_repository as repo


def run_research(db: Session, company: str, owner_id: str) -> ResearchJob:
    """Create a job row, run the pipeline, persist the outcome either way.

    A failed run is saved too (status="failed" + error) so it's visible in
    history instead of disappearing — the router decides what HTTP status
    to return based on the saved job's status.
    """
    job = repo.create_job(db, company, owner_id=owner_id)
    result = _run_research(company)
    return repo.save_result(db, job, result)
