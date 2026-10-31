"""Invoice pricing (pure domain). Owner: B.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def round_half_up(val: float | Decimal) -> int:
    """Half-up rounding to nearest integer."""
    d = Decimal(str(val)) if not isinstance(val, Decimal) else val
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_half_up_bps(amount: int, bps: int) -> int:
    """Compute round_half_up(amount * bps / 10000)."""
    return round_half_up(Decimal(amount) * Decimal(bps) / Decimal(10000))


@dataclass(frozen=True)
class LineInput:
    description: str
    quantity: int
    unit_price_minor: int
    tax_rate_bps: int = 0
    tax_inclusive: bool = False
    product_id: int | None = None
    variant_id: int | None = None
    base_price_minor: int | None = None
    variant_label: str | None = None


@dataclass(frozen=True)
class DiscountInput:
    id: int
    name: str
    kind: str  # 'fixed' (minor units) or 'percent' (basis points)
    value: int
    scope: str  # 'product' or 'subscription'
    product_id: int | None = None
    min_purchase_minor: int | None = None
    min_quantity: int | None = None


@dataclass(frozen=True)
class Applied:
    discount_id: int
    name: str
    amount_minor: int
    scope: str
    line_index: int | None = None


@dataclass
class PricedLine:
    line: LineInput
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    total_minor: int
    calc_trace: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PricedInvoice:
    lines: list[PricedLine]
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    total_minor: int
    applied: list[Applied] = field(default_factory=list)


def allocate_subscription_discount(
    net_line_subtotals: list[int],
    total_discount_minor: int,
) -> list[int]:
    """
    Allocate subscription-scope discount across lines by largest remainder
    so the sum of allocated discounts exactly equals total_discount_minor.
    """
    total_net = sum(net_line_subtotals)
    if total_net <= 0 or total_discount_minor <= 0:
        return [0] * len(net_line_subtotals)

    total_discount_minor = min(total_discount_minor, total_net)

    allocated: list[int] = []
    remainders: list[tuple[Decimal, int]] = []

    for idx, net in enumerate(net_line_subtotals):
        exact = Decimal(total_discount_minor) * Decimal(net) / Decimal(total_net)
        floor_val = int(exact)
        rem = exact - Decimal(floor_val)
        allocated.append(floor_val)
        remainders.append((rem, idx))

    leftover = total_discount_minor - sum(allocated)
    remainders.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    for i in range(leftover):
        idx = remainders[i][1]
        allocated[idx] += 1

    return allocated


def price_invoice(
    lines: list[LineInput],
    discounts: list[DiscountInput],
    as_of: date,
) -> PricedInvoice:
    """Price one invoice line by line, with a reconciling calc_trace (D-02, D-03, §13.2).

    Per line: subtotal = unit price x qty, then the best product-scope discount,
    then the best subscription-scope discount allocated by largest remainder,
    then tax after discounts. Totals are exact sums of line values; every
    trace's signed steps reconcile to the stored line total.
    """
    # 1. Product-scope discount selection per line (one best discount per line)
    product_discounts: list[DiscountInput] = [
        d for d in discounts if d.scope == "product" and d.product_id is not None
    ]

    line_subtotals: list[int] = []
    line_applied_discounts: list[Applied | None] = []

    for idx, line in enumerate(lines):
        subtotal = line.quantity * line.unit_price_minor
        line_subtotals.append(subtotal)

        best_disc: DiscountInput | None = None
        best_saving = 0

        if line.product_id is not None:
            for d in product_discounts:
                if d.product_id != line.product_id:
                    continue
                if d.min_purchase_minor is not None and subtotal < d.min_purchase_minor:
                    continue
                if d.min_quantity is not None and line.quantity < d.min_quantity:
                    continue

                saving = (
                    round_half_up_bps(subtotal, d.value)
                    if d.kind == "percent"
                    else min(d.value, subtotal)
                )
                if saving > best_saving:
                    best_saving = saving
                    best_disc = d

        if best_disc and best_saving > 0:
            line_applied_discounts.append(
                Applied(
                    discount_id=best_disc.id,
                    name=best_disc.name,
                    amount_minor=best_saving,
                    scope="product",
                    line_index=idx,
                )
            )
        else:
            line_applied_discounts.append(None)

    # 2. Subscription-scope discount selection (one best discount at subscription scope)
    sub_discounts: list[DiscountInput] = [
        d for d in discounts if d.scope == "subscription"
    ]
    post_line_subtotals = [
        line_subtotals[i] - (line_applied_discounts[i].amount_minor if line_applied_discounts[i] else 0)
        for i in range(len(lines))
    ]
    total_post_line_net = sum(post_line_subtotals)
    total_quantity = sum(line.quantity for line in lines)

    best_sub_disc: DiscountInput | None = None
    best_sub_saving = 0

    if total_post_line_net > 0:
        for d in sub_discounts:
            if d.min_purchase_minor is not None and total_post_line_net < d.min_purchase_minor:
                continue
            if d.min_quantity is not None and total_quantity < d.min_quantity:
                continue

            saving = (
                round_half_up_bps(total_post_line_net, d.value)
                if d.kind == "percent"
                else min(d.value, total_post_line_net)
            )
            if saving > best_sub_saving:
                best_sub_saving = saving
                best_sub_disc = d

    allocated_sub_discounts = allocate_subscription_discount(
        post_line_subtotals, best_sub_saving
    )

    all_applied: list[Applied] = [a for a in line_applied_discounts if a is not None]
    if best_sub_disc and best_sub_saving > 0:
        all_applied.append(
            Applied(
                discount_id=best_sub_disc.id,
                name=best_sub_disc.name,
                amount_minor=best_sub_saving,
                scope="subscription",
                line_index=None,
            )
        )

    priced_lines: list[PricedLine] = []

    for i, line in enumerate(lines):
        subtotal = line_subtotals[i]
        l_applied = line_applied_discounts[i]
        l_disc = l_applied.amount_minor if l_applied else 0
        s_disc = allocated_sub_discounts[i]
        total_line_disc = l_disc + s_disc
        net_after_all_disc = subtotal - total_line_disc

        trace: list[dict[str, Any]] = []
        if line.base_price_minor is not None and line.variant_label:
            trace.append({"label": "Product price", "amount_minor": line.base_price_minor})
            extra = line.unit_price_minor - line.base_price_minor
            trace.append({"label": f"Variant: {line.variant_label}", "amount_minor": extra})
            trace.append({"label": "Unit price", "amount_minor": line.unit_price_minor})
        else:
            trace.append({"label": line.description, "amount_minor": line.unit_price_minor})

        if line.quantity > 1:
            trace.append({"label": f"x {line.quantity} units", "amount_minor": subtotal})

        if l_disc > 0 and l_applied is not None:
            trace.append({"label": f"Discount {l_applied.name}", "amount_minor": -l_disc})

        if s_disc > 0 and best_sub_disc is not None:
            trace.append({"label": f"Discount {best_sub_disc.name} (allocated)", "amount_minor": -s_disc})

        trace.append({"label": "Net", "amount_minor": net_after_all_disc})

        rate_bps = line.tax_rate_bps
        tax_minor = 0
        line_total_minor = 0

        if rate_bps > 0:
            if line.tax_inclusive:
                net_pre_tax = round_half_up(
                    Decimal(net_after_all_disc)
                    * Decimal(10000)
                    / Decimal(10000 + rate_bps)
                )
                tax_minor = net_after_all_disc - net_pre_tax
                line_total_minor = net_after_all_disc
                rate_pct = rate_bps / 100
                trace.append(
                    {
                        "label": f"Tax {rate_pct:.1f}% (inclusive)",
                        "amount_minor": tax_minor,
                    }
                )
            else:
                tax_minor = round_half_up_bps(net_after_all_disc, rate_bps)
                line_total_minor = net_after_all_disc + tax_minor
                rate_pct = rate_bps / 100
                trace.append(
                    {
                        "label": f"Tax {rate_pct:.1f}% (exclusive)",
                        "amount_minor": tax_minor,
                    }
                )
        else:
            line_total_minor = net_after_all_disc

        trace.append({"label": "Line total", "amount_minor": line_total_minor})

        priced_lines.append(
            PricedLine(
                line=line,
                subtotal_minor=subtotal,
                discount_minor=total_line_disc,
                tax_minor=tax_minor,
                total_minor=line_total_minor,
                calc_trace=trace,
            )
        )

    inv_subtotal = sum(pl.subtotal_minor for pl in priced_lines)
    inv_discount = sum(pl.discount_minor for pl in priced_lines)
    inv_tax = sum(pl.tax_minor for pl in priced_lines)
    inv_total = sum(pl.total_minor for pl in priced_lines)

    return PricedInvoice(
        lines=priced_lines,
        subtotal_minor=inv_subtotal,
        discount_minor=inv_discount,
        tax_minor=inv_tax,
        total_minor=inv_total,
        applied=all_applied,
    )
