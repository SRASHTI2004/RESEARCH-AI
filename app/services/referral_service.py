"""Referral helper: search strings, a where-to-look checklist, and message
drafts for one job.

Deliberately deterministic templates, no LLM: instant, free, and every
claim in a draft comes from your profile or the posting — nothing is
invented. Nothing is sent and LinkedIn is never fetched: the search
strings are for *you* to paste, and the links only open LinkedIn's own
search page in your browser.
"""

from dataclasses import dataclass, field
from urllib.parse import quote_plus

from app.core.profile import Profile
from app.models.job import Job
from app.services.job_filter import has_word

LINKEDIN_NOTE_LIMIT = 300  # LinkedIn's connection-request note limit


@dataclass
class SearchString:
    label: str
    query: str
    where: str  # "LinkedIn people search" | "Google"
    url: str


@dataclass
class MessageDraft:
    kind: str  # referral_ask | connection_note | recruiter_intro | follow_up
    title: str
    body: str
    char_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.body)


@dataclass
class ReferralKit:
    search_strings: list[SearchString]
    checklist: list[str]
    drafts: list[MessageDraft]
    notes: list[str] = field(default_factory=list)


def _linkedin_people(query: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(query)}"


def _google(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def role_keyword(title: str) -> str:
    """A searchable role phrase from a posting title: drop team/level noise
    after separators ("Software Engineer, Backend (Python) - Remote")."""
    for sep in (" - ", " – ", ",", "(", "|", "/"):
        title = title.split(sep)[0]
    return title.strip() or "Software Engineer"


def matching_skills(job: Job, profile: Profile, limit: int = 3) -> list[str]:
    """Your skills that the posting actually mentions — only these go into drafts."""
    haystack = f"{job.title}\n{job.description}\n{' '.join(job.tags or [])}".lower()
    return [s for s in profile.all_skills if has_word(haystack, s.lower())][:limit]


def _search_strings(job: Job, profile: Profile) -> list[SearchString]:
    company, role = job.company, role_keyword(job.title)
    strings: list[SearchString] = []
    if profile.college:
        q = f'"{company}" "{profile.college}"'
        strings.append(
            SearchString(
                "Alumni of your college at the company", q, "LinkedIn people search", _linkedin_people(q)
            )
        )
    q = f'"{company}" "{role}"'
    strings.append(
        SearchString("People in this role at the company", q, "LinkedIn people search", _linkedin_people(q))
    )
    q = f'"{company}" (recruiter OR "talent acquisition" OR "technical recruiter") India'
    strings.append(
        SearchString("Recruiters / talent acquisition", q, "LinkedIn people search", _linkedin_people(q))
    )
    q = f'"{company}" engineering manager'
    strings.append(
        SearchString(
            "Engineering managers (likely hiring managers)", q, "LinkedIn people search", _linkedin_people(q)
        )
    )
    if profile.college:
        q = f'site:linkedin.com/in "{company}" "{profile.college}"'
        strings.append(
            SearchString("Alumni via Google (if LinkedIn search is limited)", q, "Google", _google(q))
        )
    return strings


def _checklist(job: Job, profile: Profile) -> list[str]:
    items = [
        "Confirm the posting is still open on the company's own careers page before asking anyone.",
    ]
    if profile.college:
        items.append(
            f"Alumni first: on LinkedIn open {profile.college}'s page → Alumni tab, search “{job.company}”. "
            "Shared college is the warmest intro you have."
        )
    else:
        items.append("Add `college` to config/profile.yaml to get alumni search strings (warmest intros).")
    items += [
        "Mutual connections: look for 2nd-degree connections at the company and ask them for an intro.",
        f"Engineers on the team: people with “{role_keyword(job.title)}” or a similar title — ideally 1–3 years in, "
        "they remember being freshers.",
        "Recruiters / talent acquisition at the company — best for 'is this role open to freshers?'.",
        "Seniors and college placement-cell / alumni WhatsApp or Telegram groups — someone may already work there.",
        "The company's GitHub org, tech blog or meetup talks — a specific, genuine opener for your message.",
        "Ask one or two people, not ten; never ask a stranger to refer you without reading your resume first.",
        "Have ready: the job link, the job ID if shown, and the resume tailored for this role.",
        "Log who you asked in the tracker notes and set status to “Referral asked” (follow-up in 5 days).",
    ]
    return items


def _drafts(job: Job, profile: Profile) -> list[MessageDraft]:
    me = profile.name or "[Your name]"
    role = job.title
    company = job.company
    skills = matching_skills(job, profile)
    skills_text = (
        ", ".join(skills) if skills else ", ".join(profile.primary_skills[:3]) or "[your key skills]"
    )
    college_bit = f"a {profile.college} graduate" if profile.college else "a recent graduate"
    shared = f" — saw we're both from {profile.college}" if profile.college else ""
    background = profile.headline or "fresher software developer"
    link = job.url

    referral = (
        f"Hi [Name],\n\n"
        f"I'm {me}, {college_bit} and a {background.lower()} working with {skills_text}. "
        f"I came across the {role} opening at {company} ({link}) and it lines up closely with what I've been building.\n\n"
        f"Would you be open to referring me, or pointing me to the right person? I've attached my resume tailored to "
        f"this role and am happy to share a short summary of my projects if that helps.\n\n"
        f"Thanks for your time either way!\n{me}"
    )
    note = (
        f"Hi [Name]{shared}. I'm a fresher developer ({skills_text}) applying for {role} at {company}. "
        f"Would love to connect and ask a quick question about the team."
    )
    if len(note) > LINKEDIN_NOTE_LIMIT:
        note = f"Hi [Name]{shared}. I'm applying for {role} at {company} and would love to connect."
    if len(note) > LINKEDIN_NOTE_LIMIT:
        note = note[: LINKEDIN_NOTE_LIMIT - 1] + "…"
    recruiter = (
        f"Hi [Name],\n\n"
        f"I'm {me}, {college_bit} and a {background.lower()} ({skills_text}). I'm interested in the {role} role "
        f"at {company} ({link}) and wanted to check whether it's open to freshers / recent graduates.\n\n"
        f"If it's a fit, I'd be glad to share my resume or answer any questions.\n\n"
        f"Thank you,\n{me}"
    )
    follow_up = (
        f"Hi [Name], just following up on my note about the {role} role at {company}. "
        f"I know you're busy — if a referral isn't possible, any pointer to the right person or advice on the "
        f"process would be really helpful. Thanks again!\n{me}"
    )
    return [
        MessageDraft("referral_ask", "Referral ask (alumni / employee)", referral),
        MessageDraft("connection_note", f"LinkedIn connection note (≤{LINKEDIN_NOTE_LIMIT} chars)", note),
        MessageDraft("recruiter_intro", "Recruiter intro", recruiter),
        MessageDraft("follow_up", "Follow-up (after 5–7 days, once)", follow_up),
    ]


def build_referral_kit(job: Job, profile: Profile) -> ReferralKit:
    notes = [
        "Drafts are starting points — personalise the first line for each person. Nothing is sent for you."
    ]
    if not profile.name:
        notes.append("Set `name` in config/profile.yaml so drafts are signed correctly.")
    if not matching_skills(job, profile):
        notes.append(
            "None of your profile skills appear in this posting — drafts fall back to your primary skills."
        )
    return ReferralKit(
        search_strings=_search_strings(job, profile),
        checklist=_checklist(job, profile),
        drafts=_drafts(job, profile),
        notes=notes,
    )
