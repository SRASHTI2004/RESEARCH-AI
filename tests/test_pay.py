import pytest

from app.services.pay import annual_inr, annual_inr_from_text, lpa_label


@pytest.mark.parametrize(
    "text, expected",
    [
        ("CTC: 6 LPA", 600_000),
        ("3.5 LPA", 350_000),
        ("₹ 4.5 - 6 LPA", 600_000),
        ("Salary 8-10 lakhs per annum", 1_000_000),
        ("Package: 7 lakhs", 700_000),
        ("8 lakh per annum", 800_000),
        ("₹40,000/month", 480_000),
        ("40k per month", 480_000),
        ("pay 30k-40k/month", 480_000),
        ("Stipend: 15000/month", 180_000),
        ("Rs. 25,000 - 35,000 per month", 420_000),
        ("INR 6,00,000 per annum", 600_000),
        ("Compensation: ₹12,00,000 - ₹15,00,000", 1_500_000),
        # Not pay:
        ("We serve 2 lakh users across India", None),
        ("5+ years of experience in Python", None),
        ("Raised $20M Series B", None),
        ("Founded in 2015, 500 employees", None),
    ],
)
def test_annual_inr_from_text(text, expected):
    assert annual_inr_from_text(text) == expected


def test_structured_salary_wins_and_converts_currency():
    assert annual_inr(800_000, "INR", "CTC 3 LPA") == 800_000
    assert annual_inr(1_000, "USD") == 85_000
    assert annual_inr(None, "", "CTC 6 LPA") == 600_000
    assert annual_inr(None, "") is None


def test_lpa_label():
    assert lpa_label(600_000, 800_000, "INR") == "₹6–8 LPA"
    assert lpa_label(None, 450_000, "INR") == "₹4.5 LPA"
    assert lpa_label(None, None, "") == "pay not stated"
    assert lpa_label(80_000, 100_000, "USD") == "USD 80,000–100,000"
