"""Subscription creation. Owner: C. Created as a contract stub by A."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import psycopg

from app.audit import audit
from app.clock import today
from app.services.catalog import build_line_snapshot, get_plan


def create_draft(
    conn: psycopg.Connection,
    customer_id: int,
    plan_id: int,
    start_date: date,
    expiry_date: date,
    payment_term_id: int,
    lines: list[dict[str, Any]],
    template_id: int | None = None,
    actor_id: int | None = None,
) -> int:
    """Create a Draft subscription with line snapshots and return its id.

    Validates plan availability (D-18) and min quantity (D-17). Each line dict
    carries product_id, variant_id, quantity; prices and taxes are snapshotted.
    """
    plan = get_plan(conn, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")
    if not plan["active"]:
        raise ValueError(f"Plan {plan_id} is inactive")

    # D-18: Plan availability: [available_from, available_to]
    cur_date = today()
    avail_from = plan["available_from"]
    avail_to = plan["available_to"]
    if avail_from and cur_date < avail_from:
        raise ValueError(f"Plan {plan_id} is not yet available (from {avail_from})")
    if avail_to and cur_date > avail_to:
        raise ValueError(f"Plan {plan_id} has expired (available until {avail_to})")

    if not lines:
        raise ValueError("Subscription must have at least one line item")

    min_qty = plan.get("min_quantity") or 1
    for line in lines:
        qty = line.get("quantity", 0)
        if qty < min_qty:
            raise ValueError(
                f"Line item quantity {qty} is below plan minimum quantity {min_qty} (D-17)"
            )

    sub_row = conn.execute(
        """
        INSERT INTO subscriptions (
            customer_id, plan_id, template_id, status,
            start_date, expiry_date, payment_term_id, created_by
        )
        VALUES (%s, %s, %s, 'draft', %s, %s, %s, %s)
        RETURNING id, number
        """,
        (
            customer_id,
            plan_id,
            template_id,
            start_date,
            expiry_date,
            payment_term_id,
            actor_id,
        ),
    ).fetchone()
    sub_id = int(sub_row["id"])
    sub_number = sub_row["number"]

    for line in lines:
        p_id = line["product_id"]
        v_id = line.get("variant_id")
        qty = line["quantity"]
        snapshot = build_line_snapshot(conn, p_id, v_id, qty, plan_id)

        conn.execute(
            """
            INSERT INTO subscription_lines (
                subscription_id, product_id, variant_id, quantity,
                unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                sub_id,
                p_id,
                v_id,
                qty,
                snapshot["unit_price_minor"],
                snapshot["tax_id"],
                snapshot["tax_rate_bps"],
                snapshot["tax_inclusive"],
            ),
        )

    audit(
        conn,
        actor_id,
        "subscription.create",
        "subscription",
        sub_id,
        after={
            "number": sub_number,
            "customer_id": customer_id,
            "plan_id": plan_id,
            "status": "draft",
            "start_date": str(start_date),
            "expiry_date": str(expiry_date),
            "payment_term_id": payment_term_id,
            "template_id": template_id,
            "lines_count": len(lines),
        },
    )
    return sub_id


def create_from_template(
    conn: psycopg.Connection,
    template_id: int,
    customer_id: int,
    start_date: date,
    actor_id: int | None,
) -> int:
    """Create a Draft subscription from a quotation template and return its id."""
    tmpl = conn.execute(
        """
        SELECT id, plan_id, validity_days, payment_term_id
        FROM quotation_templates
        WHERE id = %s
        """,
        (template_id,),
    ).fetchone()
    if not tmpl:
        raise ValueError(f"Quotation template {template_id} not found")

    plan_id = int(tmpl["plan_id"])
    validity_days = int(tmpl["validity_days"])
    payment_term_id = tmpl["payment_term_id"]
    if payment_term_id is None:
        # Default to first payment term if template doesn't specify
        pt = conn.execute("SELECT id FROM payment_terms ORDER BY id LIMIT 1").fetchone()
        if not pt:
            raise ValueError("No payment terms available")
        payment_term_id = int(pt["id"])

    expiry_date = start_date + timedelta(days=validity_days)

    lines_rows = conn.execute(
        """
        SELECT product_id, variant_id, quantity
        FROM quotation_template_lines
        WHERE template_id = %s
        ORDER BY id
        """,
        (template_id,),
    ).fetchall()

    lines = [
        {
            "product_id": int(r["product_id"]),
            "variant_id": int(r["variant_id"]) if r["variant_id"] is not None else None,
            "quantity": int(r["quantity"]),
        }
        for r in lines_rows
    ]

    return create_draft(
        conn,
        customer_id=customer_id,
        plan_id=plan_id,
        start_date=start_date,
        expiry_date=expiry_date,
        payment_term_id=payment_term_id,
        lines=lines,
        template_id=template_id,
        actor_id=actor_id,
    )
