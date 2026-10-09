"""Daily digest: pick the top new matches and send them to every enabled
channel. Channels are independent — one failing or unconfigured never
stops the other, and never aborts the run. Jobs are only marked as
digested if at least one channel actually delivered them.
"""

import html
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import notify
from app.core.config import settings
from app.models.job import Job
from app.repositories import application_repository

logger = logging.getLogger(__name__)


@dataclass
class DigestItem:
    job_id: str
    title: str
    company: str
    location: str
    score: int
    ai_scored: bool
    reason: str
    red_flags: list[str]
    apply_url: str
    app_url: str
    source: str
    official_source: bool
    fresher_friendly: bool | None
    posted_at: datetime | None = None
    is_remote: bool = False


@dataclass
class FollowUp:
    title: str
    company: str
    status: str
    due: date
    app_url: str


@dataclass
class DigestContent:
    items: list[DigestItem]
    follow_ups: list[FollowUp] = field(default_factory=list)
    test: bool = False

    @property
    def empty(self) -> bool:
        return not self.items and not self.follow_ups


@dataclass
class DigestResult:
    sent_items: int
    channels: dict[str, str]  # channel -> "sent" | "disabled" | "not configured" | "failed: ..."

    @property
    def delivered(self) -> bool:
        return any(status == "sent" for status in self.channels.values())


def job_app_url(job_id: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}/jobs/{job_id}"


def _to_item(job: Job) -> DigestItem:
    ai = job.llm_score is not None
    reason = job.llm_reason or ""
    if not ai:
        reason = f"Not AI-scored yet (rule match: {job.prefilter_reason})."
    return DigestItem(
        job_id=job.id,
        title=job.title,
        company=job.company,
        location=job.location or ("Remote" if job.is_remote else ""),
        score=job.score,
        ai_scored=ai,
        reason=reason,
        red_flags=list(job.red_flags or []),
        apply_url=job.url,
        app_url=job_app_url(job.id),
        source=job.source,
        official_source=job.official_source,
        fresher_friendly=job.fresher_friendly,
        posted_at=job.posted_at,
        is_remote=job.is_remote,
    )


def select_digest_jobs(db: Session, top_n: int | None = None, *, include_digested: bool = False) -> list[Job]:
    """AI-scored jobs above the minimum first (best first); if that leaves
    free slots — e.g. the LLM was down today — top up with unscored jobs by
    rule score, clearly labelled as such."""
    limit = top_n or settings.digest_top_n
    since = datetime.now(UTC) - timedelta(days=settings.digest_max_age_days)
    # Only jobs still listed at their source recently: a posting that has
    # dropped off its board has most likely been filled or closed.
    still_listed = datetime.now(UTC) - timedelta(days=3)
    base = select(Job).where(
        Job.passed_prefilter.is_(True), Job.first_seen_at >= since, Job.last_seen_at >= still_listed
    )
    if not include_digested:
        base = base.where(Job.digested_at.is_(None))

    scored = list(
        db.scalars(
            base.where(Job.llm_score >= settings.digest_min_score)
            .order_by(Job.llm_score.desc(), Job.rule_score.desc())
            .limit(limit)
        )
    )
    if len(scored) < limit:
        scored += list(
            db.scalars(
                base.where(Job.llm_score.is_(None)).order_by(Job.rule_score.desc()).limit(limit - len(scored))
            )
        )
    return scored


# --- formatting ---------------------------------------------------------------


def _header(content: DigestContent) -> str:
    prefix = "[TEST] " if content.test else ""
    return f"{prefix}Job digest — {datetime.now(UTC):%d %b %Y}"


def _score_label(item: DigestItem) -> str:
    return f"{item.score}/100" if item.ai_scored else f"{item.score}/100 (rule)"


def posted_label(posted_at: datetime | None, now: datetime | None = None) -> str:
    if posted_at is None:
        return "posting date not given"
    posted = posted_at if posted_at.tzinfo else posted_at.replace(tzinfo=UTC)
    days = ((now or datetime.now(UTC)) - posted).days
    return "posted today" if days <= 0 else f"posted {days}d ago"


def format_telegram(content: DigestContent) -> str:
    e = html.escape
    parts = [f"<b>{e(_header(content))}</b>"]
    if not content.items:
        parts.append("No new matching jobs today.")
    for i, item in enumerate(content.items, 1):
        lines = [
            f"<b>{i}. {e(item.title)}</b> — {e(item.company)}",
            f"📍 {e(item.location or 'n/a')} · ⭐ {e(_score_label(item))}"
            + (" · 🌱 fresher-friendly" if item.fresher_friendly else ""),
            e(item.reason),
            f"🗓 {posted_label(item.posted_at)}"
            + (" · 🏠 remote" if item.is_remote else "")
            + (" · ✅ company careers page" if item.official_source else f" · via {e(item.source)}"),
        ]
        if item.red_flags:
            lines.append("⚠️ Check: " + e("; ".join(item.red_flags)))
        lines.append(
            f'<a href="{e(item.apply_url, quote=True)}">Apply (via {e(item.source)})</a> · '
            f'<a href="{e(item.app_url, quote=True)}">Open in app</a>'
        )
        parts.append("\n".join(lines))
    if content.follow_ups:
        follow = ["<b>Follow-ups due</b>"] + [
            f"• {e(f.title)} — {e(f.company)} ({e(f.status)}, due {f.due:%d %b})" for f in content.follow_ups
        ]
        parts.append("\n".join(follow))
    parts.append("<i>Flags are heuristics, not verdicts — verify on the company's own careers page.</i>")
    return "\n\n".join(parts)


def format_email(content: DigestContent) -> tuple[str, str, str]:
    """Returns (subject, plain-text body, HTML body)."""
    e = html.escape
    subject = _header(content) + (f" ({len(content.items)} matches)" if content.items else "")

    text_lines = [_header(content), ""]
    for i, item in enumerate(content.items, 1):
        text_lines += [
            f"{i}. {item.title} — {item.company} ({item.location or 'n/a'}) — {_score_label(item)}",
            f"   {item.reason}",
        ]
        if item.red_flags:
            text_lines.append("   Check: " + "; ".join(item.red_flags))
        text_lines += [f"   Apply: {item.apply_url}", f"   In app: {item.app_url}", ""]
    if not content.items:
        text_lines.append("No new matching jobs today.")
    for f in content.follow_ups:
        text_lines.append(f"Follow-up due {f.due:%d %b}: {f.title} — {f.company} ({f.status})")

    cell = "padding:8px;border:1px solid #e2e2e6;vertical-align:top;font-size:14px;"
    head = "padding:8px;border:1px solid #e2e2e6;background:#f3f4f8;text-align:left;font-size:13px;"
    rows = []
    for item in content.items:
        flags = (
            "<br>".join(f"⚠️ {e(flag)}" for flag in item.red_flags)
            if item.red_flags
            else '<span style="color:#6b6b76">none</span>'
        )
        badge = " 🌱" if item.fresher_friendly else ""
        rows.append(
            "<tr>"
            f'<td style="{cell}"><b>{e(item.title)}</b>{badge}</td>'
            f'<td style="{cell}">{e(item.company)}'
            + ('<br><small style="color:#2f9e44">official board</small>' if item.official_source else "")
            + "</td>"
            f'<td style="{cell}">{e(item.location or "n/a")}</td>'
            f'<td style="{cell}white-space:nowrap"><b>{e(_score_label(item))}</b></td>'
            f'<td style="{cell}">{e(item.reason)}</td>'
            f'<td style="{cell}">{flags}</td>'
            f'<td style="{cell}white-space:nowrap"><a href="{e(item.apply_url, quote=True)}">Apply</a>'
            f'<br><small>via {e(item.source)}</small><br>'
            f'<a href="{e(item.app_url, quote=True)}">Open in app</a></td>'
            "</tr>"
        )
    table = (
        '<table style="border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif">'
        "<tr>"
        + "".join(
            f'<th style="{head}">{h}</th>'
            for h in ("Title", "Company", "Location", "Score", "Why", "Red flags", "Links")
        )
        + "</tr>"
        + "".join(rows)
        + "</table>"
        if rows
        else "<p>No new matching jobs today.</p>"
    )
    follow_html = ""
    if content.follow_ups:
        follow_html = (
            "<h3>Follow-ups due</h3><ul>"
            + "".join(
                f"<li>{e(f.title)} — {e(f.company)} ({e(f.status)}, due {f.due:%d %b}) "
                f'<a href="{e(f.app_url, quote=True)}">open</a></li>'
                for f in content.follow_ups
            )
            + "</ul>"
        )
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;color:#1a1a1f">'
        f"<h2>{e(_header(content))}</h2>{table}{follow_html}"
        '<p style="color:#6b6b76;font-size:12px">Red flags are heuristics, not verdicts — always verify '
        "on the company's own careers page. Nothing was applied to or sent on your behalf.</p></div>"
    )
    return subject, "\n".join(text_lines), html_body


# --- sending -----------------------------------------------------------------


def send_digest(content: DigestContent, *, ignore_enabled_flags: bool = False) -> DigestResult:
    """`ignore_enabled_flags` (test digest only) tries every *configured*
    channel, so setup can be verified before switching a channel on."""
    channels: dict[str, str] = {}

    if not (settings.digest_telegram_enabled or ignore_enabled_flags):
        channels["telegram"] = "disabled"
    elif not notify.telegram_configured():
        channels["telegram"] = "not configured"
    else:
        try:
            notify.send_telegram(format_telegram(content))
            channels["telegram"] = "sent"
        except notify.NotifierError as exc:
            logger.error("Digest via Telegram failed: %s", exc)
            channels["telegram"] = f"failed: {exc}"

    if not (settings.digest_email_enabled or ignore_enabled_flags):
        channels["email"] = "disabled"
    elif not notify.email_configured():
        channels["email"] = "not configured"
    else:
        try:
            notify.send_email(*format_email(content))
            channels["email"] = "sent"
        except notify.NotifierError as exc:
            logger.error("Digest via email failed: %s", exc)
            channels["email"] = f"failed: {exc}"

    return DigestResult(sent_items=len(content.items), channels=channels)


def collect_follow_ups(db: Session, today: date | None = None) -> list[FollowUp]:
    """Tracker entries whose follow-up date has arrived (overdue included)."""
    base = settings.app_base_url.rstrip("/")
    return [
        FollowUp(
            title=a.title,
            company=a.company,
            status=a.status.replace("_", " "),
            due=a.follow_up_on,
            app_url=f"{base}/tracker?focus={a.id}",
        )
        for a in application_repository.due_follow_ups(db, today or date.today())
        if a.follow_up_on is not None
    ]


def run_digest(db: Session) -> DigestResult:
    jobs = select_digest_jobs(db)
    content = DigestContent(items=[_to_item(j) for j in jobs], follow_ups=collect_follow_ups(db))
    result = send_digest(content)
    if result.delivered:
        now = datetime.now(UTC)
        for job in jobs:
            job.digested_at = now
        db.commit()
    else:
        logger.warning("Digest not delivered on any channel — jobs stay queued for the next run")
    logger.info("Digest: %d items, channels=%s", result.sent_items, result.channels)
    return result


def run_test_digest(db: Session) -> DigestResult:
    """Send what today's digest would look like (or a sample) to every
    enabled channel, without marking anything as digested."""
    jobs = select_digest_jobs(db, include_digested=True)
    items = [_to_item(j) for j in jobs]
    if not items:
        items = [
            DigestItem(
                job_id="sample",
                title="Software Engineer (sample)",
                company="Example Co",
                location="Remote - India",
                score=82,
                ai_scored=True,
                reason="Sample item — your digest setup works. Real matches appear after `python -m app.cli fetch`.",
                red_flags=[],
                apply_url="https://example.com/jobs/1",
                app_url=job_app_url("sample"),
                source="example",
                official_source=True,
                fresher_friendly=True,
            )
        ]
    content = DigestContent(items=items, follow_ups=collect_follow_ups(db), test=True)
    return send_digest(content, ignore_enabled_flags=True)
