"""Catalog price resolution. Owner: C. Created as a contract stub by A."""

from __future__ import annotations

import psycopg


def resolve_unit_price(
    conn: psycopg.Connection, product_id: int, variant_id: int | None, plan_id: int
) -> int:
    """Unit price in minor units (D-04).

    product_plan_prices override when present, else product.sales_price, plus
    the variant's extra_price (0 when no variant).
    """
    raise NotImplementedError("CONTRACT-STUB owner=C")  # CONTRACT-STUB owner=C


def build_line_snapshot(
    conn: psycopg.Connection,
    product_id: int,
    variant_id: int | None,
    quantity: int,
    plan_id: int,
) -> dict:
    """The price and tax facts snapshotted onto a subscription line (D-04).

    Returns unit_price_minor, tax_id, tax_rate_bps, tax_inclusive. Later
    catalog edits never change an existing subscription.
    """
    raise NotImplementedError("CONTRACT-STUB owner=C")  # CONTRACT-STUB owner=C
