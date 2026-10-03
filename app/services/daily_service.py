"""The once-a-day job: fetch → score → digest.

Each step is isolated: if every source fails, already-stored jobs are still
scored and sent; if the LLM is down, the digest falls back to rule-ranked
jobs. The run never raises — it reports what happened.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.jobsources import build_sources
from app.core.profile import Profile
from app.services import digest_service, job_ingest_service, scoring_service

logger = logging.getLogger(__name__)


@dataclass
class DailyReport:
    ingest: job_ingest_service.IngestSummary | None = None
    scoring: scoring_service.ScoringSummary | None = None
    digest: digest_service.DigestResult | None = None
    errors: dict[str, str] = field(default_factory=dict)


def run_daily(db: Session, profile: Profile, *, send: bool = True) -> DailyReport:
    report = DailyReport()

    try:
        report.ingest, _ = job_ingest_service.run_ingest(db, build_sources(profile), profile)
    except Exception as exc:
        logger.exception("Daily run: fetch step failed")
        db.rollback()
        report.errors["fetch"] = str(exc)

    try:
        report.scoring = scoring_service.run_scoring(db, profile)
    except Exception as exc:
        logger.exception("Daily run: scoring step failed")
        db.rollback()
        report.errors["score"] = str(exc)

    if send:
        try:
            report.digest = digest_service.run_digest(db)
        except Exception as exc:
            logger.exception("Daily run: digest step failed")
            db.rollback()
            report.errors["digest"] = str(exc)

    return report
