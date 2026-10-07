"""Evaluate the job pipeline (rule filter -> LLM scorer -> digest) and the
company-brief pipeline against a small hand-labelled test set.

    python -m evaluation.run                    # filter + red flags only: no network, no API keys
    python -m evaluation.run --llm              # + LLM scoring of the jobs that pass the filter
    python -m evaluation.run --llm --runs 3     # repeat scoring to see run-to-run spread
    python -m evaluation.run --briefs Groww Razorpay Postman

The test set and labelling rubric are described in evaluation/README.md.
Results are printed and written to evaluation/results/latest.json.
"""

import argparse
import json
import re
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core import llm
from app.core.config import settings
from app.core.profile import load_profile
from app.models.job import Job
from app.services import job_filter
from app.services.genuineness import detect_red_flags
from app.services.scoring_service import build_prompt, parse_scores

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "jobs.jsonl"
RESULTS = ROOT / "results" / "latest.json"
PROFILE = "config/profile.example.yaml"
DIGEST_SIZE = settings.digest_top_n
WORTH_APPLYING = 50  # the scorer prompt's "worth applying" line


def load_jobs() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]


def pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


# --- rule filter -------------------------------------------------------------


def run_filter(jobs: list[dict]) -> dict:
    profile = load_profile(PROFILE)
    for job in jobs:
        posted = datetime.fromisoformat(job["posted_at"]) if job["posted_at"] else None
        result = job_filter.evaluate(
            title=job["title"],
            description=job["description"],
            location=job["location"],
            is_remote=job["is_remote"],
            tags=job["tags"],
            official_source=job["official_source"],
            posted_at=posted,
            profile=profile,
        )
        job["passed"] = result.passed
        job["filter_reason"] = result.reason

    labelled = [j for j in jobs if j["label"] is not None]
    tp = sum(1 for j in labelled if j["passed"] and j["label"] == 1)
    fp = sum(1 for j in labelled if j["passed"] and j["label"] == 0)
    fn = sum(1 for j in labelled if not j["passed"] and j["label"] == 1)
    tn = sum(1 for j in labelled if not j["passed"] and j["label"] == 0)
    return {
        "labelled": len(labelled),
        "relevant": tp + fn,
        "passed": tp + fp,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "recall_pct": pct(tp, tp + fn),
        "precision_pct": pct(tp, tp + fp),
        "rejected_pct": pct(fn + tn, len(labelled)),
        "missed_relevant": [
            {"id": j["id"], "title": j["title"], "reason": j["filter_reason"]}
            for j in labelled
            if not j["passed"] and j["label"] == 1
        ],
    }


# --- red flags ---------------------------------------------------------------


def run_red_flags(jobs: list[dict]) -> dict:
    flagged = []
    for job in jobs:
        flags = detect_red_flags(title=job["title"], company=job["company"], description=job["description"])
        if flags:
            flagged.append(
                {"id": job["id"], "title": job["title"], "company": job["company"], "flags": flags}
            )
    return {
        "postings": len(jobs),
        "flagged": len(flagged),
        "flagged_pct": pct(len(flagged), len(jobs)),
        "items": flagged,
    }


# --- LLM scorer --------------------------------------------------------------


def auc(scores: list[tuple[int, int]]) -> float | None:
    """Probability a random relevant job outscores a random irrelevant one (ties count half)."""
    pos = [s for s, label in scores if label == 1]
    neg = [s for s, label in scores if label == 0]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def score_once(candidates: list[dict]) -> dict[str, dict]:
    profile = load_profile(PROFILE)
    size = max(1, settings.scoring_batch_size)
    out: dict[str, dict] = {}
    for start in range(0, len(candidates), size):
        if start:
            time.sleep(settings.scoring_min_interval_seconds)
        chunk = candidates[start : start + size]
        keyed = [
            (
                f"J{i + 1}",
                Job(
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    is_remote=j["is_remote"],
                    description=j["description"],
                ),
            )
            for i, j in enumerate(chunk)
        ]
        raw = llm.invoke_llm(build_prompt(profile, keyed), temperature=0.1, stage="scoring")
        by_key = {f"J{i + 1}": j for i, j in enumerate(chunk)}
        for entry in parse_scores(raw):
            job = by_key.get(str(entry.get("id", "")).strip("[] "))
            if job is not None and "score" in entry:
                out[job["id"]] = {
                    "score": max(0, min(100, int(entry["score"]))),
                    "fresher_friendly": bool(entry.get("fresher_friendly")),
                    "reason": str(entry.get("reason", "")),
                }
    return out


def scoring_metrics(jobs: list[dict], scores: dict[str, dict]) -> dict:
    labelled = [j for j in jobs if j["label"] is not None]
    candidates = [j for j in labelled if j["passed"]]
    scored = [(scores[j["id"]]["score"], j["label"]) for j in candidates if j["id"] in scores]
    above = [(s, label) for s, label in scored if s >= WORTH_APPLYING]

    # Digest: top N filter-passed jobs by LLM score (ties broken by id for determinism),
    # above the configured minimum score.
    ranked = sorted(
        (j for j in candidates if j["id"] in scores),
        key=lambda j: (-scores[j["id"]]["score"], j["id"]),
    )
    digest = [j for j in ranked if scores[j["id"]]["score"] >= settings.digest_min_score][:DIGEST_SIZE]
    relevant_total = sum(1 for j in labelled if j["label"] == 1)
    digest_hits = sum(1 for j in digest if j["label"] == 1)
    return {
        "scored": len(scored),
        "of_candidates": len(candidates),
        "auc": auc(scored),
        "precision_at_50_pct": pct(sum(1 for _, label in above if label == 1), len(above)),
        "recall_at_50_pct": pct(
            sum(1 for _, label in above if label == 1), sum(1 for _, label in scored if label == 1)
        ),
        "digest_size": len(digest),
        "digest_relevant": digest_hits,
        "digest_precision_pct": pct(digest_hits, len(digest)),
        "end_to_end_recall_pct": pct(digest_hits, relevant_total),
    }


def run_llm(jobs: list[dict], runs: int) -> dict:
    candidates = [j for j in jobs if j["label"] is not None and j["passed"]]
    per_run = []
    last_scores: dict[str, dict] = {}
    for i in range(runs):
        if i:
            time.sleep(settings.scoring_min_interval_seconds)
        started = time.perf_counter()
        last_scores = score_once(candidates)
        metrics = scoring_metrics(jobs, last_scores)
        metrics["seconds"] = round(time.perf_counter() - started, 1)
        per_run.append(metrics)

    summary: dict[str, Any] = {"runs": runs, "model": settings.gemini_scoring_model, "per_run": per_run}
    for key in ("auc", "precision_at_50_pct", "digest_precision_pct", "end_to_end_recall_pct"):
        values = [r[key] for r in per_run if r[key] is not None]
        if values:
            summary[key] = {"mean": round(statistics.mean(values), 3), "min": min(values), "max": max(values)}
    summary["last_run_scores"] = [
        {"id": j["id"], "title": j["title"], "label": j["label"], **last_scores[j["id"]]}
        for j in candidates
        if j["id"] in last_scores
    ]
    return summary


# --- company briefs ----------------------------------------------------------

# "[3]" or a combined "[2, 6]"
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_SECTION_END = re.compile(r"^#+\s*(sources|references|verification notes)\b", re.IGNORECASE | re.MULTILINE)


def brief_metrics(report: str, source_count: int) -> dict:
    """Checks on the brief body (everything before Sources / Verification Notes):
    how many factual lines carry a citation, and whether every [n] points at a real source."""
    cut = _SECTION_END.search(report)
    body = report[: cut.start()] if cut else report
    lines = [
        line.strip(" -*\t")
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and len(line.split()) >= 6
    ]
    cited = [line for line in lines if _CITATION.search(line)]
    numbers = [int(n) for group in _CITATION.findall(body) for n in group.split(",")]
    invalid = [n for n in numbers if not 1 <= n <= source_count]
    notes = report[cut.start() :] if cut else ""
    return {
        "claim_lines": len(lines),
        "cited_lines": len(cited),
        "citation_coverage_pct": pct(len(cited), len(lines)),
        "citations": len(numbers),
        "invalid_citations": len(invalid),
        "reviewer_found_issues": "no issues found" not in notes.lower(),
    }


def run_briefs(companies: list[str], pause: int, save_to: Path | None = None) -> dict:
    from app.pipeline.graph import run_research  # heavy import (LangGraph); only when needed

    results = []
    saved = []
    for index, company in enumerate(companies):
        if index:
            time.sleep(pause)  # free-tier tokens-per-minute limits; back-to-back briefs get rate limited
        started = time.perf_counter()
        state = run_research(company)
        elapsed = round(time.perf_counter() - started, 1)
        row: dict[str, Any] = {"company": company, "status": state["status"], "seconds": elapsed}
        if state["status"] == "done":
            row["sources"] = len(state["sources"])
            row.update(brief_metrics(state["final_report"], len(state["sources"])))
            saved.append(
                {
                    "company": company,
                    "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "research": state["research"],
                    "analysis": state["analysis"],
                    "report": state["report"],
                    "final_report": state["final_report"],
                    "sources": [
                        {k: s.get(k, "") for k in ("index", "title", "url", "snippet")}
                        for s in state["sources"]
                    ],
                }
            )
        else:
            row["error"] = state.get("error")
        results.append(row)

    if save_to and saved:
        save_to.write_text(json.dumps(saved, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    done = [r for r in results if r["status"] == "done"]
    summary: dict[str, Any] = {
        "companies": len(results),
        "completed": len(done),
        "model": settings.gemini_model,
        "items": results,
    }
    if done:
        summary["mean_seconds"] = round(statistics.mean(r["seconds"] for r in done), 1)
        summary["mean_sources"] = round(statistics.mean(r["sources"] for r in done), 1)
        summary["citation_coverage_pct"] = pct(
            sum(r["cited_lines"] for r in done), sum(r["claim_lines"] for r in done)
        )
        summary["invalid_citations"] = sum(r["invalid_citations"] for r in done)
        summary["total_citations"] = sum(r["citations"] for r in done)
    return summary


# --- main --------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--llm", action="store_true", help="also score filter-passed jobs with the LLM")
    parser.add_argument("--runs", type=int, default=1, help="LLM scoring repetitions (default 1)")
    parser.add_argument(
        "--briefs", nargs="*", default=[], metavar="COMPANY", help="companies to generate briefs for"
    )
    parser.add_argument("--pause", type=int, default=90, help="seconds between briefs (default 90)")
    parser.add_argument(
        "--save-briefs", type=Path, help="also write the generated briefs (demo fixture format)"
    )
    args = parser.parse_args()

    jobs = load_jobs()
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": {"postings": len(jobs), "labelled": sum(1 for j in jobs if j["label"] is not None)},
        "filter": run_filter(jobs),
        "red_flags": run_red_flags(jobs),
    }
    if args.llm:
        report["llm_scoring"] = run_llm(jobs, args.runs)
    if args.briefs:
        report["briefs"] = run_briefs(args.briefs, args.pause, args.save_briefs)

    # Keep results from earlier runs for the parts that weren't re-run this time.
    if RESULTS.exists():
        previous = json.loads(RESULTS.read_text(encoding="utf-8"))
        for key in ("llm_scoring", "briefs"):
            if key not in report and key in previous:
                report[key] = previous[key]
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    f = report["filter"]
    print(f"Dataset: {report['dataset']['labelled']} labelled postings, {f['relevant']} relevant")
    print(
        f"Rule filter: recall {f['recall_pct']}%  precision {f['precision_pct']}%  "
        f"rejects {f['rejected_pct']}% of postings  (confusion {f['confusion']})"
    )
    for miss in f["missed_relevant"]:
        print(f"  missed: {miss['id']} {miss['title']} -- {miss['reason']}")
    rf = report["red_flags"]
    print(f"Red flags: {rf['flagged']}/{rf['postings']} postings flagged ({rf['flagged_pct']}%)")
    if "llm_scoring" in report:
        s = report["llm_scoring"]
        print(f"LLM scoring ({s['runs']} run(s), {s['model']}):")
        for key in ("auc", "precision_at_50_pct", "digest_precision_pct", "end_to_end_recall_pct"):
            if key in s:
                print(f"  {key}: mean {s[key]['mean']}  range {s[key]['min']}-{s[key]['max']}")
    if "briefs" in report:
        b = report["briefs"]
        print(f"Briefs: {b['completed']}/{b['companies']} completed")
        for key in (
            "mean_seconds",
            "mean_sources",
            "citation_coverage_pct",
            "invalid_citations",
            "total_citations",
        ):
            if key in b:
                print(f"  {key}: {b[key]}")
    print(f"Wrote {RESULTS.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
