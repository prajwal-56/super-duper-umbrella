"""Subscription creation. Owner: C. Created as a contract stub by A."""

from __future__ import annotations

from datetime import date

import psycopg


def create_draft(
    conn: psycopg.Connection,
    customer_id: int,
    plan_id: int,
    start_date: date,
    expiry_date: date,
    payment_term_id: int,
    lines: list[dict],
    template_id: int | None = None,
    actor_id: int | None = None,
) -> int:
    """Create a Draft subscription with line snapshots and return its id.

    Validates plan availability (D-18) and min quantity (D-17). Each line dict
    carries product_id, variant_id, quantity; prices and taxes are snapshotted.
    """
    raise NotImplementedError("CONTRACT-STUB owner=C")  # CONTRACT-STUB owner=C


def create_from_template(
    conn: psycopg.Connection,
    template_id: int,
    customer_id: int,
    start_date: date,
    actor_id: int | None,
) -> int:
    """Create a Draft subscription from a quotation template and return its id."""
    raise NotImplementedError("CONTRACT-STUB owner=C")  # CONTRACT-STUB owner=C
