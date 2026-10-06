"""Command-line entry point for the Job Search Assistant.

python -m app.cli fetch [--force] [--sources greenhouse,remotive]
python -m app.cli refilter
python -m app.cli sources
python -m app.cli score [--limit 30]
python -m app.cli digest
python -m app.cli test-digest
python -m app.cli run-daily      # fetch + score + digest (what the scheduler runs)
python -m app.cli seed-demo      # reset the demo account (DEMO_ENABLED=true)
"""

import argparse
import sys

from app.core.db import SessionLocal
from app.core.jobsources import ALL_SOURCE_NAMES, build_sources
from app.core.logging import configure_logging
from app.core.profile import load_profile
from app.repositories import job_repository
from app.services import daily_service, demo_service, digest_service, job_ingest_service, scoring_service


def _split(value: str | None) -> list[str] | None:
    return [v.strip() for v in value.split(",") if v.strip()] if value else None


def cmd_fetch(args: argparse.Namespace) -> int:
    profile = load_profile()
    db = SessionLocal()
    try:
        sources = build_sources(profile, _split(args.sources))
        summary, _ = job_ingest_service.run_ingest(db, sources, profile, force=args.force)
    finally:
        db.close()
    print(
        f"Fetched {summary.fetched} postings: {summary.new} new "
        f"({summary.new_passing} pass the filter), {summary.updated} already known."
    )
    for name, why in summary.sources_skipped.items():
        print(f"  skipped {name}: {why}")
    for name, err in summary.sources_failed.items():
        print(f"  FAILED  {name}: {err}")
    return 0


def cmd_refilter(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        count = job_ingest_service.refilter_all(db, load_profile())
    finally:
        db.close()
    print(f"Re-applied filter rules to {count} jobs.")
    return 0


def cmd_sources(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        runs = {r.source: r for r in job_repository.latest_runs(db)}
    finally:
        db.close()
    for name in ALL_SOURCE_NAMES:
        run = runs.get(name)
        if run is None:
            print(f"{name:15} never fetched")
        else:
            print(
                f"{name:15} {run.status:7} {run.started_at:%Y-%m-%d %H:%M} "
                f"fetched={run.fetched_count} new={run.new_count} {run.message[:80]}"
            )
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        summary = scoring_service.run_scoring(db, load_profile(), limit=args.limit)
    finally:
        db.close()
    print(f"Scored {summary.scored}/{summary.candidates} jobs ({summary.failed_batches} failed batches).")
    return 0


def _print_channels(result: digest_service.DigestResult) -> None:
    for channel, status in result.channels.items():
        print(f"  {channel:9} {status}")


def cmd_digest(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = digest_service.run_digest(db)
    finally:
        db.close()
    print(f"Digest with {result.sent_items} jobs:")
    _print_channels(result)
    return 0 if result.delivered else 1


def cmd_test_digest(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        result = digest_service.run_test_digest(db)
    finally:
        db.close()
    print("Test digest (tries every configured channel, marks nothing as sent):")
    _print_channels(result)
    return 0 if result.delivered else 1


def cmd_run_daily(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        report = daily_service.run_daily(db, load_profile())
    finally:
        db.close()
    if report.ingest:
        print(f"Fetch: {report.ingest.new} new jobs ({report.ingest.new_passing} pass the filter)")
        for name, err in report.ingest.sources_failed.items():
            print(f"  source FAILED {name}: {err}")
    if report.scoring:
        print(f"Score: {report.scoring.scored}/{report.scoring.candidates} scored")
    if report.digest:
        print(f"Digest: {report.digest.sent_items} jobs")
        _print_channels(report.digest)
    for step, err in report.errors.items():
        print(f"STEP FAILED {step}: {err}")
    return 1 if report.errors else 0


def cmd_seed_demo(_args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        summary = demo_service.seed_demo(db)
    except demo_service.DemoDisabledError:
        print("DEMO_ENABLED is off; nothing to do.")
        return 0
    finally:
        db.close()
    print(
        f"Demo seeded: {summary.jobs_added} sample jobs added, "
        f"{summary.applications} tracker entries, {summary.briefs} briefs"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Job Search Assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Fetch new jobs from all enabled sources")
    fetch.add_argument("--force", action="store_true", help="Ignore per-source minimum polling intervals")
    fetch.add_argument("--sources", help="Comma-separated subset of sources to run")
    fetch.set_defaults(func=cmd_fetch)

    refilter = sub.add_parser(
        "refilter", help="Re-apply filter rules to all stored jobs (after editing profile)"
    )
    refilter.set_defaults(func=cmd_refilter)

    sources = sub.add_parser("sources", help="Show the last run of each source")
    sources.set_defaults(func=cmd_sources)

    score = sub.add_parser("score", help="LLM-score the top unscored jobs against your profile")
    score.add_argument("--limit", type=int, default=None, help="Max jobs to score (default SCORING_MAX_JOBS)")
    score.set_defaults(func=cmd_score)

    digest = sub.add_parser("digest", help="Send today's digest to the enabled channels")
    digest.set_defaults(func=cmd_digest)

    test_digest = sub.add_parser("test-digest", help="Send a test digest to every configured channel")
    test_digest.set_defaults(func=cmd_test_digest)

    daily = sub.add_parser("run-daily", help="Fetch + score + digest (what the scheduler runs)")
    daily.set_defaults(func=cmd_run_daily)

    seed = sub.add_parser("seed-demo", help="Create/reset the demo account and its sample data")
    seed.set_defaults(func=cmd_seed_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
