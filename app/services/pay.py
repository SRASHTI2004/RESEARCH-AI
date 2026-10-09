"""Reading stated pay out of a posting, in annual INR.

Indian postings write pay many ways: "6 LPA", "8-10 lakhs per annum",
"₹40,000/month", "40k per month", "INR 6,00,000 per annum",
"Stipend: 15000/month". Structured salary fields (Adzuna) win when present;
otherwise the text is scanned. Only stated numbers count: nothing is guessed,
and an estimate (Adzuna's salary_is_predicted) is never stored as a salary.
"""

import re

# Rough conversion for remote roles paid in other currencies; only used to
# compare against an INR floor, never shown as a converted amount.
_TO_INR = {"INR": 1.0, "USD": 85.0, "EUR": 92.0, "GBP": 108.0, "CAD": 62.0, "AUD": 56.0, "SGD": 64.0}

_CUR = r"(?:₹|rs\.?|inr)?\s*"
_SEP = r"\s*(?:-|–|to)\s*"
_NUM = r"(\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)"
_SMALL = r"(\d{1,2}(?:\.\d+)?)"

_LPA = re.compile(
    rf"{_CUR}{_SMALL}(?:{_SEP}{_CUR}{_SMALL})?\s*(lpa|l\.p\.a\.?|lakhs?|lacs?)\b",
    re.IGNORECASE,
)
# "lakh" on its own is also used for counts ("2 lakh users"), so it only counts
# next to a pay word; "LPA" is unambiguous.
_PAY_BEFORE = re.compile(
    r"salary|ctc|pay|package|compensation|stipend|offer|remuneration|₹|rs\.?|inr", re.IGNORECASE
)
_PAY_AFTER = re.compile(
    r"^\s*(?:per annum|p\.?\s?a\.?(?!\w)|/\s*annum|annum|ctc|per year|a year)", re.IGNORECASE
)

_K_MONTH = re.compile(
    rf"{_CUR}(\d{{1,3}})\s*k(?:{_SEP}{_CUR}(\d{{1,3}})\s*k)?\s*(?:/|per|a)\s*(?:month|mo)\b",
    re.IGNORECASE,
)
_AMOUNT = re.compile(
    rf"(?:₹|rs\.?|inr)\s*{_NUM}(?:{_SEP}(?:₹|rs\.?|inr)?\s*{_NUM})?"
    r"\s*(?:/|per|a)?\s*(month|mo|annum|year|yr|p\.?a\.?|p\.?m\.?)?\b",
    re.IGNORECASE,
)
_PLAIN_MONTH = re.compile(rf"{_NUM}(?:{_SEP}{_NUM})?\s*(?:/|per)\s*month\b", re.IGNORECASE)


def _num(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def annual_inr_from_text(text: str) -> int | None:
    """Highest stated annual pay in INR, or None if the text states none."""
    found: list[float] = []
    for m in _LPA.finditer(text):
        if not m.group(3).lower().startswith(("lpa", "l.p")):
            before, after = text[max(0, m.start() - 40) : m.start()], text[m.end() : m.end() + 15]
            if not (_PAY_BEFORE.search(before) or _PAY_AFTER.search(after)):
                continue
        found += [n * 100_000 for n in (_num(m.group(1)), _num(m.group(2))) if n]
    for m in _K_MONTH.finditer(text):
        found += [n * 1_000 * 12 for n in (_num(m.group(1)), _num(m.group(2))) if n]
    for m in _AMOUNT.finditer(text):
        unit = (m.group(3) or "").lower().replace(".", "")
        for n in (_num(m.group(1)), _num(m.group(2))):
            if not n or n < 1_000:
                continue
            monthly = unit in {"month", "mo", "pm"} or (not unit and n < 100_000)
            found.append(n * 12 if monthly else n)
    for m in _PLAIN_MONTH.finditer(text):
        found += [n * 12 for n in (_num(m.group(1)), _num(m.group(2))) if n and 1_000 <= n < 1_000_000]
    plausible = [v for v in found if 50_000 <= v <= 50_000_000]
    return int(max(plausible)) if plausible else None


def annual_inr(salary_max: float | None, salary_currency: str, text: str = "") -> int | None:
    """Structured salary (converted to INR) if present, else what the text states."""
    if salary_max:
        rate = _TO_INR.get((salary_currency or "INR").upper())
        if rate:
            return int(salary_max * rate)
    return annual_inr_from_text(text) if text else None


def lpa_label(salary_min: float | None, salary_max: float | None, salary_currency: str) -> str:
    """'₹6–8 LPA', '₹5 LPA', 'USD 90,000', or 'pay not stated'."""
    if not salary_max:
        return "pay not stated"
    currency = (salary_currency or "INR").upper()
    if currency != "INR":
        low = f"{salary_min:,.0f}–" if salary_min and salary_min != salary_max else ""
        return f"{currency} {low}{salary_max:,.0f}"

    def fmt(v: float) -> str:
        return f"{v / 100_000:.1f}".rstrip("0").rstrip(".")

    if salary_min and salary_min < salary_max:
        return f"₹{fmt(salary_min)}–{fmt(salary_max)} LPA"
    return f"₹{fmt(salary_max)} LPA"
