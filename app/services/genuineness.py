"""Heuristic red-flag detection for job postings.

These are *signals worth a second look*, not verdicts — a flag never
removes a job, and a job with no flags isn't proven genuine. The UI and
digest word them that way on purpose.
"""

import re

_FEE = re.compile(
    r"\b(registration|training|security|joining|processing|application|onboarding|kit)\s+(fee|fees|deposit|charges?)\b"
    r"|\bpay\s+(?:a\s+|the\s+)?(?:small\s+)?fee\b|\brefundable\s+deposit\b|\binvestment\s+(?:is\s+)?required\b",
    re.IGNORECASE,
)
_MESSAGING = re.compile(r"\b(telegram|whatsapp)\b|\bwa\.me/|\bt\.me/", re.IGNORECASE)
_PERSONAL_EMAIL = re.compile(
    r"[\w.+-]+@(?:gmail|yahoo|hotmail|outlook|rediffmail|ymail|protonmail|aol|icloud)\.(?:com|in|co\.in)",
    re.IGNORECASE,
)
_GUARANTEE = re.compile(
    r"\b(guaranteed\s+(?:job|placement|income|selection)|no\s+interview|100%\s+(?:job|placement))\b",
    re.IGNORECASE,
)
_EASY_MONEY = re.compile(
    r"\bearn\s+(?:up\s+to\s+)?(?:\$|₹|rs\.?|inr)\s?[\d,]+\s*(?:k\b)?\s*(?:per|a|/)\s*(?:day|week)\b"
    r"|\b(?:\$|₹)\s?[\d,]+\s*/\s*(?:day|week)\b|\bcommission[- ]only\b|\bmlm\b",
    re.IGNORECASE,
)
_JUNIOR = re.compile(
    r"\b(junior|jr|fresher|entry[- ]level|intern|internship|trainee|graduate)\b", re.IGNORECASE
)
_GIG = re.compile(
    r"\bai (?:code |coding )?trainer\b|data annotat|\brlhf\b|\bper hour\b|\d\s*/\s*h(?:ou)?r\b|\bhourly rate\b"
    r"|\bfreelance\b|\bgig\b|\bcontract(?:or)? (?:role|position|basis)\b",
    re.IGNORECASE,
)
_VAGUE_COMPANY = {"", "confidential", "stealth", "undisclosed", "hiring company", "company", "n/a", "na"}

# Annual pay above which a junior/intern role is suspicious.
_UNREALISTIC_JUNIOR_PAY = {"USD": 200_000, "INR": 5_000_000, "EUR": 180_000, "GBP": 150_000}


def detect_red_flags(
    *,
    title: str,
    company: str,
    description: str,
    salary_max: float | None = None,
    salary_currency: str = "",
) -> list[str]:
    flags: list[str] = []

    if _FEE.search(description):
        flags.append("Mentions a fee or deposit — genuine employers don't charge candidates")
    if _MESSAGING.search(description):
        flags.append("Mentions Telegram/WhatsApp contact — verify the recruiter on the company's own site")
    email = _PERSONAL_EMAIL.search(description)
    if email:
        flags.append(f"Contact uses a personal email domain ({email.group(0).split('@')[1]})")
    if _GUARANTEE.search(description):
        flags.append("Promises a guaranteed job/placement or no interview")
    if _EASY_MONEY.search(description):
        flags.append("Pay pitched per day/week or commission-only — check it's a real salaried role")

    limit = _UNREALISTIC_JUNIOR_PAY.get(salary_currency.upper())
    if limit and salary_max and salary_max > limit and _JUNIOR.search(title):
        flags.append(f"Unusually high pay for a junior role ({salary_currency} {salary_max:,.0f})")

    if _GIG.search(title) or _GIG.search(description):
        flags.append("Looks like hourly/contract gig work, not a salaried job")

    if company.strip().lower() in _VAGUE_COMPANY or len(company.strip()) < 2:
        flags.append("Company name is missing or vague")
    if len(description.strip()) < 200:
        flags.append("Very short description — little to verify the role against")

    return flags
