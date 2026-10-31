"""Discount selection (pure domain). Owner: B. Created as a contract stub by A."""

from __future__ import annotations

from datetime import date

from app.domain.pricing import Applied, DiscountInput, LineInput


def select(
    lines: list[LineInput],
    candidates: list[DiscountInput],
    as_of: date,
) -> list[Applied]:
    """Choose the discounts that apply to one invoice (D-11).

    At most one best discount per line (product scope) plus at most one best
    discount at subscription scope, applied to the post-line-discount subtotal.
    Best = largest saving; ties go to the earliest end date. Eligibility needs
    an active rule, as_of inside [starts_on, ends_on], min purchase/quantity
    met within scope and usage remaining.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
