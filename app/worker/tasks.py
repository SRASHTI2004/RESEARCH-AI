import logging

from app.core.db import SessionLocal
from app.pipeline.graph import create_graph
from app.repositories import research_repository as repo
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _initial_state(company: str) -> dict:
    return {
        "company": company,
        "research": "",
        "analysis": "",
        "report": "",
        "final_report": "",
        "sources": [],
        "status": "pending",
        "error": None,
    }


@celery_app.task(name="run_research_job")
def run_research_job(job_id: str, company: str) -> None:
    """Runs the pipeline stage-by-stage, persisting progress after each one.

    Uses graph.stream() rather than .invoke() specifically so the job row's
    status advances through researching -> analyzing -> writing -> done as
    each stage actually completes, instead of jumping straight from
    "pending" to the final result — that's what lets the frontend show live
    per-stage progress by polling GET /research/{id}.
    """
    db = SessionLocal()
    try:
        job = repo.get_job(db, job_id)
        if job is None:
            logger.warning("run_research_job: job %s no longer exists, skipping", job_id)
            return

        state = _initial_state(company)

        for update in create_graph().stream(state):
            for _node_name, state_after in update.items():
                state = state_after
                repo.save_result(db, job, state)
    except Exception as exc:
        # Last-resort safety net for a bug/crash outside the pipeline's own
        # per-stage error handling (which already sets status="failed" in
        # state and is persisted above via the normal loop).
        logger.exception("run_research_job: unhandled error for job %s", job_id)
        job = repo.get_job(db, job_id)
        if job is not None:
            repo.save_result(db, job, {**_initial_state(company), "status": "failed", "error": str(exc)})
    finally:
        db.close()
