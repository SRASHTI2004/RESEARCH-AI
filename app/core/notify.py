"""Outbound notification channels for the daily digest.

Each channel raises NotifierError with a message that has already had its
secret scrubbed — the Telegram bot token is part of the API *URL*, so a
raw `requests` exception would otherwise leak it into logs.
"""

import smtplib
from email.message import EmailMessage

import requests

from app.core.config import settings

TELEGRAM_MAX_CHARS = 4096


class NotifierError(Exception):
    """A channel failed. The message is safe to log."""


def _is_set(value: str) -> bool:
    """Blank or still the .env.example placeholder ("your-...-here") = not set."""
    return bool(value) and not value.startswith("your-")


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


# --- Telegram ---------------------------------------------------------------


def telegram_configured() -> bool:
    return _is_set(settings.telegram_bot_token) and _is_set(settings.telegram_chat_id)


def split_for_telegram(text: str, limit: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Split on blank lines so no HTML tag or item is cut in half."""
    chunks: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = block[:limit]
    if current:
        chunks.append(current)
    return chunks


def send_telegram(text: str) -> None:
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in split_for_telegram(text):
        try:
            res = requests.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            body = res.json() if res.content else {}
        except (requests.RequestException, ValueError) as exc:
            raise NotifierError(_redact(f"Telegram request failed: {exc}", token)) from None
        if res.status_code != 200 or not body.get("ok", False):
            description = body.get("description", res.reason) if isinstance(body, dict) else res.reason
            raise NotifierError(_redact(f"Telegram API error {res.status_code}: {description}", token))


# --- Email (SMTP, e.g. Gmail with an App Password) -------------------------


def email_configured() -> bool:
    return all(_is_set(v) for v in (settings.smtp_username, settings.smtp_password, settings.digest_email_to))


def send_email(subject: str, text_body: str, html_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.digest_email_from or settings.smtp_username
    message["To"] = settings.digest_email_to
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise NotifierError(_redact(f"SMTP failed: {exc}", settings.smtp_password)) from None
