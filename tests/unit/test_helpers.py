"""Offline tests for framework helpers - no browser or UAT access needed."""
from decimal import Decimal

import pytest

from pages.dashboard_page import account_matches
from utils import masking
from utils.money import format_amount, parse_amount, to_decimal
from utils.safety import UnsafeEnvironmentError, assert_safe_url

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text, expected", [
    ("RM 1,250.50", Decimal("1250.50")),
    ("RM1250.5", Decimal("1250.50")),
    ("MYR 10,000.00", Decimal("10000.00")),
    ("1,250.50", Decimal("1250.50")),
    ("-RM 50.00", Decimal("-50.00")),
    ("RM -50.00", Decimal("-50.00")),
    ("(RM 50.00)", Decimal("-50.00")),
    ("RM 50.00 DR", Decimal("-50.00")),
    ("RM 50.00 CR", Decimal("50.00")),
    ("RM 1,000.00", Decimal("1000.00")),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("bad", ["", "RM", "abc", "RM 1.2.3", None])
def test_parse_amount_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_amount(bad)


def test_decimal_arithmetic_is_exact():
    assert parse_amount("RM 0.30") - parse_amount("RM 0.10") == Decimal("0.20")
    assert format_amount(Decimal("1250.5")) == "1250.50"
    with pytest.raises(TypeError):
        to_decimal(0.1)


@pytest.mark.parametrize("url", [
    "https://prod.yourbank.example", "https://www.yourbank.example",
    "https://live.yourbank.example", "https://ib-PROD.bank.example", "",
])
def test_safety_guard_refuses_unsafe_urls(url):
    with pytest.raises(UnsafeEnvironmentError):
        assert_safe_url(url)


def test_safety_guard_allows_uat():
    assert_safe_url("https://uat.yourbank.example")


def test_mask_account_keeps_last_four():
    assert masking.mask_account("1234 5678 9012") == "****9012"


def test_mask_text_masks_registered_and_generic_values():
    masking.register_account("5555666677778888")
    masking.register_secret("S3cret!Pass")
    text = "acct 5555-6666-7777-8888 pw S3cret!Pass other 112233445566 time 10:22:33 amt 1250.50"

    masked = masking.mask_text(text)

    assert "5555-6666-7777-8888" not in masked and "****8888" in masked
    assert "S3cret!Pass" not in masked
    assert "112233445566" not in masked and "****5566" in masked
    assert "10:22:33" in masked and "1250.50" in masked


@pytest.mark.parametrize("shown, account, expected", [
    ("1234567890", "1234567890", True),
    ("****7890", "1234567890", True),
    ("Savings ****7890", "1234567890", True),
    ("****7891", "1234567890", False),
    ("1234567891", "1234567890", False),
    ("", "1234567890", False),
])
def test_account_matches(shown, account, expected):
    assert account_matches(shown, account) is expected
