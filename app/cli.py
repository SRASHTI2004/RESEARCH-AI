"""Command-line entry point for the Job Search Assistant.

python -m app.cli fetch [--force] [--sources greenhouse,remotive]
python -m app.cli refilter
python -m app.cli sources
"""

import argparse
import sys

from app.core.db import SessionLocal
from app.core.jobsources import ALL_SOURCE_NAMES, build_sources
from app.core.logging import configure_logging
from app.core.profile import load_profile
from app.repositories import job_repository
from app.services import job_ingest_service


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
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
