"""Invoice pricing (pure domain). Owner: B. Created as a contract stub by A.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


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
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
