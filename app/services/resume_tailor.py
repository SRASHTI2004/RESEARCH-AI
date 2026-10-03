"""Tailor the master resume to one job — without inventing anything.

Division of labour:
- **Code orders.** Projects, bullets within each item, and skills within
  each group are re-ranked by how many of the job's technologies they
  mention. Experience stays in your (chronological) order. Nothing is
  ever dropped or added.
- **The LLM only rewords** the summary and individual bullets, returned as
  JSON keyed by bullet ID.
- **A validator has the final say.** Each reworded bullet is checked
  against *its own original item*: no new numbers, no technology the item
  never mentioned, no new proper nouns (companies, products), no padding.
  A failing rewrite is discarded — the original wording is kept and you get
  a warning saying why. If the LLM is unavailable, you still get the
  keyword-based reordering.
"""

import difflib
import json
import logging
import re
from dataclasses import dataclass, field

from app.core import llm
from app.core.resume import Experience, Project, Resume
from app.models.job import Job
from app.services.resume_keywords import find_terms, is_term
from app.services.scoring_service import excerpt

logger = logging.getLogger(__name__)

JOB_EXCERPT_CHARS = 2500

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NUMBER_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "fifteen", "twenty", "thirty", "fifty", "hundred", "hundreds", "thousand", "thousands", "million",
    "millions", "dozen", "dozens", "double", "doubled", "triple", "tripled", "half", "halved",
}  # fmt: skip
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]*")
# Capitalised acronyms common in rewording that don't name a company/product.
_ALLOWED_CAPS = {
    "API",
    "APIS",
    "UI",
    "UX",
    "CI",
    "CD",
    "CRUD",
    "MVP",
    "HTTP",
    "JSON",
    "SDK",
    "CLI",
    "ETL",
    "QA",
}


@dataclass
class DiffLine:
    op: str  # " " unchanged | "-" removed | "+" added
    text: str


@dataclass
class TailorResult:
    resume: Resume
    warnings: list[str]
    keywords_matched: list[str]
    keywords_missing: list[str]
    used_llm: bool
    diff: list[DiffLine] = field(default_factory=list)


# --- facts extraction ---------------------------------------------------------


def numbers_in(text: str) -> set[str]:
    found = {n.replace(",", "") for n in _NUMBER.findall(text)}
    found |= {w for w in re.findall(r"[a-z]+", text.lower()) if w in _NUMBER_WORDS}
    return found


def _words(text: str) -> set[str]:
    return {w.lower().strip(".-") for w in _WORD.findall(text)}


def new_proper_nouns(new: str, allowed_text: str) -> set[str]:
    """Capitalised words mid-sentence that appear nowhere in the allowed text."""
    allowed = _words(allowed_text)
    found = set()
    for sentence in re.split(r"(?<=[.!?;:])\s+", new):
        tokens = _WORD.findall(sentence)
        for token in tokens[1:]:  # first word of a sentence is capitalised anyway
            clean = token.strip(".-")
            if (
                clean[:1].isupper()
                and clean.upper() not in _ALLOWED_CAPS
                and clean.lower() not in allowed
                and not is_term(clean)  # technologies are policed by the term check instead
            ):
                found.add(clean)
    return found


def _item_text(item: Experience | Project) -> str:
    head = f"{item.title} {item.org}" if isinstance(item, Experience) else item.name
    return "\n".join([head, *item.tech, *item.bullets])


def check_rewrite(original: str, new: str, *, allowed_text: str, skills: list[str]) -> str | None:
    """Returns why a rewrite must be rejected, or None if it's safe."""
    if not new.strip():
        return "empty rewrite"
    if len(new) > max(len(original) * 1.5, len(original) + 60):
        return "much longer than the original (padding)"
    extra_numbers = numbers_in(new) - numbers_in(original)
    if extra_numbers:
        return f"adds numbers not in the original ({', '.join(sorted(extra_numbers))})"
    extra_terms = find_terms(new, skills) - find_terms(allowed_text, skills)
    if extra_terms:
        return f"mentions technologies this item never used ({', '.join(sorted(extra_terms))})"
    nouns = new_proper_nouns(new, allowed_text)
    if nouns:
        return f"introduces names not in your resume ({', '.join(sorted(nouns))})"
    return None


# --- ordering (deterministic) ---------------------------------------------------


def _relevance(text: str, job_terms: set[str], skills: list[str]) -> int:
    return len(find_terms(text, skills) & job_terms)


def reorder(master: Resume, job_terms: set[str]) -> Resume:
    skills = [i for g in master.skills for i in g.items]
    resume = master.model_copy(deep=True)

    for group in resume.skills:
        group.items.sort(key=lambda s: s.lower() not in job_terms)  # stable: matches first
    items: list[Experience | Project] = [*resume.experience, *resume.projects]
    for item in items:
        item.bullets.sort(key=lambda b: -_relevance(b, job_terms, skills))
    resume.projects.sort(key=lambda p: -_relevance(_item_text(p), job_terms, skills))
    return resume


# --- LLM rewording -------------------------------------------------------------------


def _bullet_index(resume: Resume) -> dict[str, tuple[Experience | Project, int]]:
    index: dict[str, tuple[Experience | Project, int]] = {}
    for exp in resume.experience:
        for i in range(len(exp.bullets)):
            index[f"exp:{exp.id}:{i}"] = (exp, i)
    for proj in resume.projects:
        for i in range(len(proj.bullets)):
            index[f"proj:{proj.id}:{i}"] = (proj, i)
    return index


def build_prompt(resume: Resume, job: Job, matched: list[str]) -> str:
    index = _bullet_index(resume)
    items = []
    entries: list[Experience | Project] = [*resume.experience, *resume.projects]
    for item in entries:
        label = f"{item.title} at {item.org}" if isinstance(item, Experience) else f"Project: {item.name}"
        prefix = "exp" if isinstance(item, Experience) else "proj"
        bullets = {
            key: item.bullets[i] for key, (it, i) in index.items() if it is item and key.startswith(prefix)
        }
        items.append({"item": label, "tech": item.tech, "bullets": bullets})

    return f"""You are tailoring a candidate's resume to one job. You may ONLY reword what is already there.

JOB: {job.title} at {job.company}
Technologies the candidate genuinely has that this job wants: {", ".join(matched) or "none"}
Job description (excerpt):
{excerpt(job.description, JOB_EXCERPT_CHARS)}

CURRENT SUMMARY:
{resume.summary}

RESUME ITEMS (bullets keyed by id):
{json.dumps(items, indent=1, ensure_ascii=False)}

Return ONLY a JSON object: {{"summary": "...", "bullets": {{"<bullet id>": "<reworded bullet>"}}}}

Strict rules:
- Never add a fact. Do not add any technology, tool, number, metric, team size, user count, company, product or outcome that is not already in THAT bullet or its item's tech list.
- Keep the same meaning and scope; don't upgrade "helped build" to "led".
- You may use the job's vocabulary for things the bullet already says (e.g. "REST API endpoints" -> "RESTful APIs").
- Only include bullets you actually changed; leave out bullets that are already well aligned.
- Each bullet: starts with a past-tense action verb, max 30 words, plain text, no markdown.
- Summary: 2-3 sentences built only from facts in the resume above."""


def _parse(raw: str) -> dict:
    text = re.sub(r"```(?:json)?", "", raw)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in LLM response")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")
    return data


def apply_rewrites(resume: Resume, master: Resume, data: dict, job: Job) -> list[str]:
    """Apply validated rewrites in place; returns warnings for rejected ones."""
    warnings: list[str] = []
    skills = [i for g in master.skills for i in g.items]
    index = _bullet_index(resume)

    bullets = data.get("bullets") or {}
    if isinstance(bullets, dict):
        for key, new in bullets.items():
            target = index.get(str(key))
            if target is None or not isinstance(new, str):
                continue
            item, i = target
            original = item.bullets[i]
            new = new.strip().lstrip("-•* ").strip()
            if new == original:
                continue
            reason = check_rewrite(original, new, allowed_text=_item_text(item), skills=skills)
            if reason:
                warnings.append(f"Kept your original wording for “{original[:60]}…”: the rewrite {reason}.")
                continue
            item.bullets[i] = new

    summary = data.get("summary")
    if isinstance(summary, str) and summary.strip() and summary.strip() != master.summary:
        new_summary = summary.strip()
        # The summary may draw on the whole resume (numbers included), and may name the target role.
        allowed = f"{master.all_text()}\n{job.title}"
        reason = (
            "is longer than 600 characters"
            if len(new_summary) > 600
            else check_rewrite(allowed, new_summary, allowed_text=allowed, skills=skills)
        )
        if reason:
            warnings.append(f"Kept your original summary: the rewrite {reason}.")
        else:
            resume.summary = new_summary
    return warnings


# --- rendering + diff -------------------------------------------------------------


def render_text(resume: Resume) -> list[str]:
    """Plain-text rendering — used for the diff (and mirrors the export layout)."""
    c = resume.contact
    lines = [c.name, " | ".join(x for x in [c.email, c.phone, c.location, *c.links.values()] if x), ""]
    if resume.summary:
        lines += ["SUMMARY", resume.summary, ""]
    if resume.skills:
        lines += ["SKILLS", *[f"{g.group}: {', '.join(g.items)}" for g in resume.skills], ""]
    if resume.experience:
        lines.append("EXPERIENCE")
        for e in resume.experience:
            lines.append(
                f"{e.title} — {e.org}{f', {e.location}' if e.location else ''} ({e.start} – {e.end})"
            )
            lines += [f"- {b}" for b in e.bullets]
        lines.append("")
    if resume.projects:
        lines.append("PROJECTS")
        for p in resume.projects:
            tech = f" | {', '.join(p.tech)}" if p.tech else ""
            lines.append(f"{p.name}{tech}")
            lines += [f"- {b}" for b in p.bullets]
        lines.append("")
    if resume.education:
        lines.append("EDUCATION")
        for ed in resume.education:
            score = f", {ed.score}" if ed.score else ""
            lines.append(f"{ed.degree} — {ed.school} ({ed.start} – {ed.end}){score}")
        lines.append("")
    if resume.achievements:
        lines += ["ACHIEVEMENTS", *[f"- {a}" for a in resume.achievements]]
    return lines


def diff_lines(master: Resume, tailored: Resume) -> list[DiffLine]:
    return [
        DiffLine(op=line[0], text=line[2:])
        for line in difflib.ndiff(render_text(master), render_text(tailored))
        if not line.startswith("?")
    ]


# --- entry point -------------------------------------------------------------------


def tailor(master: Resume, job: Job, *, use_llm: bool = True) -> TailorResult:
    skills = [i for g in master.skills for i in g.items]
    job_terms = find_terms(f"{job.title}\n{job.description}", skills)
    master_terms = find_terms(master.all_text(), skills)
    matched = sorted(job_terms & master_terms)
    missing = sorted(job_terms - master_terms)

    resume = reorder(master, job_terms)
    warnings: list[str] = []
    used_llm = False

    if use_llm:
        try:
            raw = llm.invoke_llm(build_prompt(resume, job, matched), temperature=0.2, stage="tailoring")
            warnings += apply_rewrites(resume, master, _parse(raw), job)
            used_llm = True
        except (llm.LLMError, ValueError) as exc:
            logger.warning("Resume rewording unavailable, using reorder-only tailoring: %s", exc)
            warnings.append(
                "AI rewording was unavailable — this version is reordered for the job but not reworded."
            )

    return TailorResult(
        resume=resume,
        warnings=warnings,
        keywords_matched=matched,
        keywords_missing=missing,
        used_llm=used_llm,
        diff=diff_lines(master, resume),
    )
