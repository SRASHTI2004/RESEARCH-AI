"""Fetch → normalize → dedupe → store → pre-filter.

Every source is isolated: one failing or slow board is logged and recorded
as an `error` SourceRun, and the rest of the run carries on.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.jobsources.base import JobSource, NormalizedJob
from app.core.jobsources.text import ensure_utc
from app.core.profile import Profile
from app.models.job import Job, SourceRun
from app.repositories import job_repository as repo
from app.services import job_filter
from app.services.genuineness import detect_red_flags

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    new_passing: int = 0
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)
    sources_skipped: dict[str, str] = field(default_factory=dict)


def _apply_rules(job: Job, profile: Profile) -> None:
    result = job_filter.evaluate(
        title=job.title,
        description=job.description,
        location=job.location,
        is_remote=job.is_remote,
        tags=job.tags or [],
        official_source=job.official_source,
        posted_at=job.posted_at,
        profile=profile,
    )
    job.passed_prefilter = result.passed
    job.prefilter_reason = result.reason
    job.rule_score = result.rule_score
    job.red_flags = detect_red_flags(
        title=job.title,
        company=job.company,
        description=job.description,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
    )


def _copy_posting(job: Job, posting: NormalizedJob) -> None:
    job.source = posting.source
    job.external_id = posting.external_id[:500]
    job.official_source = posting.official_source
    job.title = posting.title[:300]
    job.company = posting.company[:200]
    job.location = posting.location[:500]
    job.is_remote = posting.is_remote
    job.url = posting.url[:1000]
    job.description = posting.description
    job.employment_type = posting.employment_type[:100]
    job.tags = [t for t in posting.tags if t][:30]
    job.salary_text = posting.salary_text[:200]
    job.salary_min = posting.salary_min
    job.salary_max = posting.salary_max
    job.salary_currency = posting.salary_currency[:10]
    job.posted_at = posting.posted_at


def _prefer(a: NormalizedJob, b: NormalizedJob) -> NormalizedJob:
    """Official company boards win over aggregator re-posts; otherwise keep
    whichever has the fuller description."""
    if a.official_source != b.official_source:
        return a if a.official_source else b
    return a if len(a.description) >= len(b.description) else b


def dedupe(postings: list[NormalizedJob]) -> list[NormalizedJob]:
    best: dict[str, NormalizedJob] = {}
    for posting in postings:
        if not posting.title or not posting.url:
            continue
        key = posting.fingerprint
        best[key] = _prefer(best[key], posting) if key in best else posting
    return list(best.values())


def _due(db: Session, source: JobSource, now: datetime) -> tuple[bool, str]:
    last = repo.last_successful_run(db, source.name)
    started = ensure_utc(last.started_at) if last else None
    if started is not None and now - started < timedelta(hours=source.min_interval_hours):
        return False, f"fetched {started:%Y-%m-%d %H:%M} UTC; min interval {source.min_interval_hours:g}h"
    return True, ""


def fetch_all(
    db: Session, sources: list[JobSource], *, force: bool = False, summary: IngestSummary
) -> list[tuple[str, list[NormalizedJob]]]:
    now = datetime.now(UTC)
    results: list[tuple[str, list[NormalizedJob]]] = []
    for source in sources:
        if not source.is_configured():
            summary.sources_skipped[source.name] = "not configured"
            continue
        if not force:
            due, why = _due(db, source, now)
            if not due:
                summary.sources_skipped[source.name] = why
                continue

        run = SourceRun(source=source.name, started_at=datetime.now(UTC), status="ok")
        try:
            postings = source.fetch()
            run.fetched_count = len(postings)
            results.append((source.name, postings))
            summary.sources_ok.append(source.name)
        except Exception as exc:
            logger.warning("Job source '%s' failed: %s", source.name, exc)
            run.status = "error"
            run.message = str(exc)[:1000]
            summary.sources_failed[source.name] = str(exc)[:200]
        run.finished_at = datetime.now(UTC)
        repo.record_source_run(db, run)
    return results


def store(db: Session, postings: list[NormalizedJob], profile: Profile, summary: IngestSummary) -> list[Job]:
    """Upsert deduped postings. Returns only the jobs created this run."""
    now = datetime.now(UTC)
    created: list[Job] = []
    for posting in dedupe(postings):
        existing = repo.get_by_fingerprint(db, posting.fingerprint)
        if existing is not None:
            existing.last_seen_at = now
            # An official listing showing up later replaces the aggregator copy.
            if posting.official_source and not existing.official_source:
                _copy_posting(existing, posting)
                _apply_rules(existing, profile)
            summary.updated += 1
            continue

        job = Job(fingerprint=posting.fingerprint, first_seen_at=now, last_seen_at=now)
        _copy_posting(job, posting)
        _apply_rules(job, profile)
        repo.add(db, job)
        created.append(job)
    db.commit()

    summary.new += len(created)
    summary.new_passing += sum(1 for j in created if j.passed_prefilter)
    return created


def run_ingest(
    db: Session, sources: list[JobSource], profile: Profile, *, force: bool = False
) -> tuple[IngestSummary, list[Job]]:
    summary = IngestSummary()
    per_source = fetch_all(db, sources, force=force, summary=summary)
    postings = [p for _, batch in per_source for p in batch]
    summary.fetched = len(postings)
    created = store(db, postings, profile, summary)

    # Record how many brand-new jobs each source contributed (UI status).
    created_by_source: dict[str, int] = {}
    for job in created:
        created_by_source[job.source] = created_by_source.get(job.source, 0) + 1
    for run in repo.latest_runs(db):
        if run.source in created_by_source and run.status == "ok":
            run.new_count = created_by_source[run.source]
    db.commit()

    logger.info(
        "Ingest: fetched=%d new=%d (passing filter=%d) updated=%d ok=%s failed=%s skipped=%s",
        summary.fetched,
        summary.new,
        summary.new_passing,
        summary.updated,
        summary.sources_ok,
        list(summary.sources_failed),
        list(summary.sources_skipped),
    )
    return summary, created


def refilter_all(db: Session, profile: Profile) -> int:
    """Re-run the rules over every stored job — after editing profile.yaml."""
    jobs = repo.all_jobs(db)
    for job in jobs:
        _apply_rules(job, profile)
    db.commit()
    return len(jobs)
