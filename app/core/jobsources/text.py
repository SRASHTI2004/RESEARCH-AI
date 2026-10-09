import html
import re
from datetime import UTC, datetime

_BLOCK_TAGS = re.compile(r"<\s*(?:br|/p|/div|/ul|/ol|/h[1-6]|/tr)\s*/?>", re.IGNORECASE)
_LI = re.compile(r"<\s*li[^>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")

MAX_DESCRIPTION_CHARS = 20_000


# UTF-8 bytes that were decoded as Latin-1 upstream ("â" instead of "–").
_MOJIBAKE = re.compile("[ÂÃâ][-¿]")


def fix_mojibake(text: str) -> str:
    if not _MOJIBAKE.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def html_to_text(raw: str | None) -> str:
    """Good-enough HTML → plain text for job descriptions. Unescapes first
    because Greenhouse returns HTML that is itself entity-escaped."""
    if not raw:
        return ""
    text = fix_mojibake(html.unescape(raw))
    text = _BLOCK_TAGS.sub("\n", text)
    text = _LI.sub("\n- ", text)
    text = _TAGS.sub(" ", text)
    text = html.unescape(text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_LINES.sub("\n\n", text).strip()
    return text[:MAX_DESCRIPTION_CHARS]


def ensure_utc(value: datetime | None) -> datetime | None:
    """SQLite hands timezone-aware columns back as naive datetimes (they
    were stored as UTC) — re-attach UTC so comparisons work on both
    SQLite and Postgres."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def parse_datetime(value: str | int | float | None) -> datetime | None:
    """Accepts ISO-8601 strings, RFC-822 (RSS), or epoch seconds/millis."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, int | float):
            seconds = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(seconds, tz=UTC)
        text = str(value).strip()
        if text.isdigit():
            return parse_datetime(int(text))
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            from email.utils import parsedate_to_datetime

            parsed = parsedate_to_datetime(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (ValueError, TypeError, OverflowError):
        return None
