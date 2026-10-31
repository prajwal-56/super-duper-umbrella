"""Money helpers. Amounts are integer minor units (D-01); never floats."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_STRIP = {"₹": "", "INR": "", "Rs.": "", "Rs": "", " ": "", ",": "", "_": ""}


def fmt(minor: int) -> str:
    """Format minor units with Indian digit grouping, two decimals, no symbol.

    fmt(12345600) -> '1,23,456.00'; fmt(-500) -> '(5.00)'.
    """
    minor = int(minor)
    negative = minor < 0
    whole, cents = divmod(abs(minor), 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    text = f"{digits}.{cents:02d}"
    return f"({text})" if negative else text


def parse(text: str) -> int:
    """Parse a human-entered amount into minor units.

    Accepts '1,23,456.00', ' 1234.5 ', '(5.00)', '₹1,234', 'INR 1,234.56'.
    Raises ValueError for anything that is not a plain amount.
    """
    if text is None:
        raise ValueError("amount is required")
    raw = str(text).strip()
    if not raw:
        raise ValueError("amount is required")
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1]
    for token, replacement in _STRIP.items():
        raw = raw.replace(token, replacement)
    if raw.startswith("-"):
        negative = True
        raw = raw[1:]
    if raw.startswith("+"):
        raw = raw[1:]
    if not raw:
        raise ValueError("amount is required")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"not an amount: {text!r}") from exc
    if amount.as_tuple().exponent < -2:
        raise ValueError("amount has more than 2 decimal places")
    minor = int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return -minor if negative else minor


def round_half_up_bps(amount: int, bps: int) -> int:
    """amount * bps / 10000 rounded half-up, sign preserved, integer arithmetic."""
    amount = int(amount)
    bps = int(bps)
    sign = -1 if amount < 0 else 1
    magnitude = abs(amount) * bps
    return sign * ((magnitude + 5000) // 10000)


def bps(rate: Decimal | str) -> int:
    """Turn '18%' or Decimal('0.18') into basis points (1800)."""
    text = str(rate).strip()
    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1].strip()
    value = Decimal(text)
    if is_percent:
        value = value / 100
    return int((value * 10000).to_integral_value(rounding=ROUND_HALF_UP))
