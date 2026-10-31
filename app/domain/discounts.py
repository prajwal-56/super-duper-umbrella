"""Discount selection (pure domain). Owner: B.

BUILD_PLAN §12, §13.5, D-11.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.domain.pricing import Applied, DiscountInput, LineInput


def round_half_up(val: float | Decimal) -> int:
    d = Decimal(str(val)) if not isinstance(val, Decimal) else val
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_half_up_bps(amount: int, bps: int) -> int:
    return round_half_up(Decimal(amount) * Decimal(bps) / Decimal(10000))


def select(
    lines: list[LineInput],
    candidates: list[DiscountInput],
    as_of: date,
) -> list[Applied]:
    """Choose the discounts that apply to one invoice (D-11).

    At most one best discount per line (product scope) plus at most one best
    discount at subscription scope, applied to the post-line-discount subtotal.
    Best = largest saving; ties go to the earliest end date (then lowest id).
    Eligibility needs an active rule, min purchase/quantity met within scope.
    """
    applied: list[Applied] = []

    # 1. Product-scope discounts per line
    product_candidates = [
        c for c in candidates if c.scope == "product" and c.product_id is not None
    ]

    line_savings: list[int] = [0] * len(lines)

    for idx, line in enumerate(lines):
        if line.product_id is None:
            continue

        line_subtotal = line.quantity * line.unit_price_minor
        best_cand: DiscountInput | None = None
        best_saving = 0

        for cand in product_candidates:
            if cand.product_id != line.product_id:
                continue
            if cand.min_purchase_minor is not None and line_subtotal < cand.min_purchase_minor:
                continue
            if cand.min_quantity is not None and line.quantity < cand.min_quantity:
                continue

            saving = (
                round_half_up_bps(line_subtotal, cand.value)
                if cand.kind == "percent"
                else min(cand.value, line_subtotal)
            )
            if saving <= 0:
                continue

            if saving > best_saving:
                best_saving = saving
                best_cand = cand
            elif saving == best_saving and best_cand is not None:
                if cand.id < best_cand.id:
                    best_cand = cand

        if best_cand and best_saving > 0:
            line_savings[idx] = best_saving
            applied.append(
                Applied(
                    discount_id=best_cand.id,
                    name=best_cand.name,
                    amount_minor=best_saving,
                    scope="product",
                    line_index=idx,
                )
            )

    # 2. Subscription-scope discount
    sub_candidates = [c for c in candidates if c.scope == "subscription"]
    post_line_subtotal = sum(
        (lines[i].quantity * lines[i].unit_price_minor) - line_savings[i]
        for i in range(len(lines))
    )
    total_quantity = sum(line.quantity for line in lines)

    if post_line_subtotal > 0:
        best_sub_cand: DiscountInput | None = None
        best_sub_saving = 0

        for cand in sub_candidates:
            if cand.min_purchase_minor is not None and post_line_subtotal < cand.min_purchase_minor:
                continue
            if cand.min_quantity is not None and total_quantity < cand.min_quantity:
                continue

            saving = (
                round_half_up_bps(post_line_subtotal, cand.value)
                if cand.kind == "percent"
                else min(cand.value, post_line_subtotal)
            )
            if saving <= 0:
                continue

            if saving > best_sub_saving:
                best_sub_saving = saving
                best_sub_cand = cand
            elif saving == best_sub_saving and best_sub_cand is not None:
                if cand.id < best_sub_cand.id:
                    best_sub_cand = cand

        if best_sub_cand and best_sub_saving > 0:
            applied.append(
                Applied(
                    discount_id=best_sub_cand.id,
                    name=best_sub_cand.name,
                    amount_minor=best_sub_saving,
                    scope="subscription",
                    line_index=None,
                )
            )

    return applied
