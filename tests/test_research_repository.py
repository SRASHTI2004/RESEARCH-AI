from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.repositories import research_repository as repo


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_create_job_defaults_to_pending():
    db = _session()
    job = repo.create_job(db, "Acme Corp")
    assert job.id
    assert job.status == "pending"
    assert job.company == "Acme Corp"


def test_save_result_persists_sources_in_order():
    db = _session()
    job = repo.create_job(db, "Acme Corp")

    result = {
        "status": "done",
        "error": None,
        "research": "r",
        "analysis": "a",
        "report": "rep",
        "final_report": "final",
        "sources": [
            {"index": 2, "title": "Second", "url": "https://b", "snippet": "b"},
            {"index": 1, "title": "First", "url": "https://a", "snippet": "a"},
        ],
    }
    updated = repo.save_result(db, job, result)

    assert updated.status == "done"
    assert updated.final_report == "final"
    assert [s.index for s in updated.sources] == [1, 2]  # ordered by index, not insertion order


def test_get_job_returns_none_for_unknown_id():
    db = _session()
    assert repo.get_job(db, "nope") is None


def test_list_jobs_respects_limit():
    db = _session()
    for i in range(3):
        repo.create_job(db, f"Company {i}")

    assert len(repo.list_jobs(db, limit=2)) == 2
