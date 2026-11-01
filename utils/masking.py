"""Masking of account numbers and secrets in logs, reports and screenshots.

Account numbers keep only their last 4 digits ("****1234").
Passwords and OTPs are fully masked ("****") - even partial reveal is a leak.
"""
from __future__ import annotations

import re

SECRET_MASK = "****"
MIN_SECRET_LENGTH = 4

# Any standalone run of 8-19 digits is treated as a possible account/card number.
GENERIC_ACCOUNT_PATTERN = r"(?<![A-Za-z0-9_])\d{8,19}(?![A-Za-z0-9_])"

_secrets: set[str] = set()
_account_patterns: dict[str, re.Pattern[str]] = {}
_generic_account_re = re.compile(GENERIC_ACCOUNT_PATTERN)


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def mask_account(number: str) -> str:
    """'1234 5678 9012' -> '****9012'."""
    digits = digits_only(number)
    if not digits:
        return SECRET_MASK
    return SECRET_MASK + digits[-4:]


def _account_pattern_source(number: str) -> str | None:
    digits = digits_only(number)
    if len(digits) < 6:
        return None
    # Match the digits even when the app formats them with spaces or dashes.
    # The syntax is shared with JavaScript (used for screenshot masking).
    return r"(?<!\d)" + r"[ -]?".join(digits) + r"(?!\d)"


def register_account(number: str) -> None:
    source = _account_pattern_source(number)
    if source:
        _account_patterns[source] = re.compile(source)


def register_secret(value: str) -> None:
    if value and len(value) >= MIN_SECRET_LENGTH:
        _secrets.add(value)


def mask_text(text: str) -> str:
    """Mask registered secrets, registered account numbers and generic digit runs."""
    if not text:
        return text
    for secret in sorted(_secrets, key=len, reverse=True):
        text = text.replace(secret, SECRET_MASK)
    for pattern in _account_patterns.values():
        text = pattern.sub(lambda m: mask_account(m.group(0)), text)
    return _generic_account_re.sub(lambda m: mask_account(m.group(0)), text)


def account_pattern_sources() -> list[str]:
    """Regex sources (JS-compatible) for masking account numbers in the browser."""
    return [*_account_patterns.keys(), GENERIC_ACCOUNT_PATTERN]


def secrets_for_browser_masking() -> list[str]:
    return sorted(_secrets, key=len, reverse=True)
