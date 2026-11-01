"""Money helpers. All money values are Decimal - never float."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
_CURRENCY = re.compile(r"MYR|RM", re.IGNORECASE)


def to_decimal(value: str | int | Decimal) -> Decimal:
    """Convert a plain number ("100", "10.5", 7) to a 2-dp Decimal. Floats are rejected."""
    if isinstance(value, float):
        raise TypeError("Use str or Decimal for money, not float")
    try:
        return Decimal(str(value).strip()).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"Not a valid amount: {value!r}") from exc


def parse_amount(text: str) -> Decimal:
    """Parse a displayed amount into a Decimal.

    Handles: "RM 1,250.50", "RM1250.5", "MYR 1,250.50", "-RM 50.00",
    "RM -50.00", "(RM 50.00)", "RM 50.00 DR", "1,250.50".
    """
    if text is None:
        raise ValueError("Cannot parse amount from None")
    raw = text.strip()
    if not raw:
        raise ValueError("Cannot parse amount from empty text")

    negative = False
    work = raw
    if work.startswith("(") and work.endswith(")"):
        negative, work = True, work[1:-1]
    if re.search(r"\bDR\b", work, re.IGNORECASE):
        negative = True
    work = re.sub(r"\b(DR|CR)\b", "", work, flags=re.IGNORECASE)
    work = _CURRENCY.sub("", work)
    work = work.replace(",", "").replace(" ", "").replace(" ", "")
    if work.startswith("-"):
        negative, work = not negative, work[1:]
    elif work.startswith("+"):
        work = work[1:]

    if not re.fullmatch(r"\d+(\.\d+)?", work):
        raise ValueError(f"Not a valid amount: {raw!r}")

    amount = Decimal(work).quantize(CENT, rounding=ROUND_HALF_UP)
    return -amount if negative else amount


def format_amount(amount: Decimal | str) -> str:
    """Format a Decimal for typing into an amount field, e.g. Decimal('1250.5') -> '1250.50'."""
    return f"{to_decimal(amount):.2f}"
