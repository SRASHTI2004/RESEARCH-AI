from typing import Any

import pytest

from app.services.genuineness import detect_red_flags
from tests.factories import GOOD_DESCRIPTION


def _flags(**overrides):
    args: dict[str, Any] = {"title": "Software Engineer", "company": "Acme", "description": GOOD_DESCRIPTION}
    args.update(overrides)
    return detect_red_flags(**args)


def test_clean_posting_has_no_flags():
    assert _flags() == []


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("A refundable registration fee of Rs 2000 applies.", "fee"),
        ("You must pay a small fee for the training kit.", "fee"),
        ("Contact HR on WhatsApp at +91 99999 99999.", "Telegram/WhatsApp"),
        ("Join our Telegram group t.me/jobs123 to apply", "Telegram/WhatsApp"),
        ("Send your CV to hr.hiring2026@gmail.com", "personal email domain (gmail.com)"),
        ("Guaranteed placement after the course!", "guaranteed"),
        ("Earn up to $500 per day from home", "per day/week"),
        ("This is a commission-only role", "commission-only"),
    ],
)
def test_red_flag_patterns(snippet, expected):
    flags = _flags(description=f"{GOOD_DESCRIPTION} {snippet}")
    assert any(expected.lower() in f.lower() for f in flags), flags


def test_unrealistic_pay_for_junior_role():
    flags = _flags(title="Junior Developer", salary_max=350_000, salary_currency="USD")
    assert any("Unusually high pay" in f for f in flags)
    # Same pay for a non-junior title isn't flagged by this rule.
    assert not any("Unusually high pay" in f for f in _flags(salary_max=350_000, salary_currency="USD"))


def test_vague_company_and_short_description():
    flags = _flags(company="Confidential", description="Great job. Apply now.")
    assert any("Company name" in f for f in flags)
    assert any("short description" in f for f in flags)
