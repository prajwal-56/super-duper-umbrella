"""Billing engine entry points (database logic). Owner: B.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.audit import audit
from app.clock import today
from app.domain.periods import expected_periods
from app.domain.pricing import (
    DiscountInput,
    LineInput,
    price_invoice,
)


def _json_serializable(obj: Any) -> Any:
    if isinstance(obj, (date,)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_serializable(x) for x in obj]
    return obj


def bill_subscription(
    conn: psycopg.Connection,
    subscription_id: int,
    as_of: date | None = None,
    actor_id: int | None = None,
    run_id: int | None = None,
    auto_confirm: bool = False,
) -> list[int]:
    """Bill every missing period of one subscription inside the caller's transaction.

    Returns the invoice ids created. Periods are derived from facts (D-25);
    discounts are claimed atomically (D-11); duplicate periods are blocked by
    the partial unique index. Each invoice line stores its calc_trace.
    """
    if as_of is None:
        as_of = today()

    # 1. Lock subscription row
    sub = conn.execute(
        """
        SELECT s.*, p.billing_interval, p.interval_count, p.price_minor as plan_price_minor,
               pt.due_days
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
          JOIN payment_terms pt ON pt.id = s.payment_term_id
         WHERE s.id = %(id)s
           FOR UPDATE
        """,
        {"id": subscription_id},
    ).fetchone()

    if not sub:
        return []

    # 2. Fetch pauses
    pauses_rows = conn.execute(
        """
        SELECT paused_on, resumed_on
          FROM subscription_pauses
         WHERE subscription_id = %(id)s
         ORDER BY paused_on
        """,
        {"id": subscription_id},
    ).fetchall()
    pauses: list[tuple[date, date | None]] = [
        (p["paused_on"], p["resumed_on"]) for p in pauses_rows
    ]

    # 3. Derive expected periods
    expected = expected_periods(
        start=sub["start_date"],
        expiry=sub["expiry_date"],
        unit=sub["billing_interval"],
        count=sub["interval_count"],
        as_of=as_of,
        closed_on=sub["closed_on"],
        pauses=pauses,
        cap=36,
    )

    # 4. Fetch existing invoices (including cancelled)
    existing_invoices = conn.execute(
        """
        SELECT period_start, status
          FROM invoices
         WHERE subscription_id = %(id)s
        """,
        {"id": subscription_id},
    ).fetchall()
    existing_map = {row["period_start"]: row["status"] for row in existing_invoices}

    # 5. Fetch subscription lines
    sub_lines = conn.execute(
        """
        SELECT sl.*, p.name as product_name
          FROM subscription_lines sl
          JOIN products p ON p.id = sl.product_id
         WHERE sl.subscription_id = %(id)s
         ORDER BY sl.id
        """,
        {"id": subscription_id},
    ).fetchall()

    # 6. Fetch attached discount rules + auto_apply discounts active as of this period
    candidate_discounts = conn.execute(
        """
        SELECT d.*
          FROM discounts d
         WHERE d.active = true
           AND (
                d.auto_apply = true
             OR d.id IN (
                SELECT discount_id FROM subscription_discounts WHERE subscription_id = %(sub_id)s
             )
           )
        """,
        {"sub_id": subscription_id},
    ).fetchall()

    created_invoice_ids: list[int] = []

    for period in expected:
        # Skip paused periods (D-08)
        if period.paused:
            continue

        # Skip already invoiced or cancelled periods (D-15)
        if period.start in existing_map:
            continue

        # Missing period found -> Bill it under a savepoint
        savepoint_name = f"sp_bill_{subscription_id}_{period.index}"
        conn.execute(f"SAVEPOINT {savepoint_name}")

        try:
            # Build LineInput objects
            pricing_lines: list[LineInput] = []
            for sl in sub_lines:
                pricing_lines.append(
                    LineInput(
                        description=sl["product_name"],
                        quantity=sl["quantity"],
                        unit_price_minor=sl["unit_price_minor"],
                        tax_rate_bps=sl["tax_rate_bps"],
                        tax_inclusive=sl["tax_inclusive"],
                        product_id=sl["product_id"],
                        variant_id=sl["variant_id"],
                    )
                )

            # D-04: Plan fee line if plan.price_minor > 0
            if sub["plan_price_minor"] > 0:
                pricing_lines.append(
                    LineInput(
                        description="Plan fee",
                        quantity=1,
                        unit_price_minor=sub["plan_price_minor"],
                        tax_rate_bps=0,
                        tax_inclusive=False,
                    )
                )

            # Filter eligible discounts for period.start
            eligible_discounts: list[DiscountInput] = []
            for cd in candidate_discounts:
                if cd["starts_on"] <= period.start <= cd["ends_on"]:
                    if cd["usage_limit"] is None or cd["usage_count"] < cd["usage_limit"]:
                        eligible_discounts.append(
                            DiscountInput(
                                id=cd["id"],
                                name=cd["name"],
                                kind=cd["kind"],
                                value=cd["value"],
                                scope=cd["scope"],
                                product_id=cd["product_id"],
                                min_purchase_minor=cd["min_purchase_minor"],
                                min_quantity=cd["min_quantity"],
                            )
                        )

            # Atomic discount claiming (§13.5)
            # We first price to determine which discounts apply
            priced = price_invoice(pricing_lines, eligible_discounts, as_of=period.start)

            claimed_discounts: list[tuple[int, int]] = []  # (discount_id, amount_minor)
            retry_pricing = False

            for app_disc in priced.applied:
                # Try atomic claim
                res = conn.execute(
                    """
                    UPDATE discounts
                       SET usage_count = usage_count + 1
                     WHERE id = %(id)s
                       AND (usage_limit IS NULL OR usage_count < usage_limit)
                 RETURNING id
                    """,
                    {"id": app_disc.discount_id},
                ).fetchone()

                if not res:
                    # Discount exhausted! Drop it and re-price
                    eligible_discounts = [
                        d for d in eligible_discounts if d.id != app_disc.discount_id
                    ]
                    retry_pricing = True
                    break
                else:
                    claimed_discounts.append((app_disc.discount_id, app_disc.amount_minor))

            if retry_pricing:
                # Rollback to release any partial claims
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                conn.execute(f"SAVEPOINT {savepoint_name}")
                priced = price_invoice(pricing_lines, eligible_discounts, as_of=period.start)
                claimed_discounts = []
                for app_disc in priced.applied:
                    res = conn.execute(
                        """
                        UPDATE discounts
                           SET usage_count = usage_count + 1
                         WHERE id = %(id)s
                           AND (usage_limit IS NULL OR usage_count < usage_limit)
                     RETURNING id
                        """,
                        {"id": app_disc.discount_id},
                    ).fetchone()
                    if res:
                        claimed_discounts.append((app_disc.discount_id, app_disc.amount_minor))

            issue_d = as_of
            due_d = issue_d + timedelta(days=sub["due_days"])

            # Insert invoice with idempotency conflict check
            inv = conn.execute(
                """
                INSERT INTO invoices (
                    subscription_id, customer_id, period_start, period_end,
                    issue_date, due_date, status, subtotal_minor, discount_minor,
                    tax_minor, total_minor, amount_paid_minor, billing_run_id
                ) VALUES (
                    %(sub_id)s, %(cust_id)s, %(p_start)s, %(p_end)s,
                    %(issue)s, %(due)s, 'draft', %(subtotal)s, %(discount)s,
                    %(tax)s, %(total)s, 0, %(run_id)s
                )
                ON CONFLICT (subscription_id, period_start) WHERE status <> 'cancelled'
                DO NOTHING
                RETURNING id
                """,
                {
                    "sub_id": subscription_id,
                    "cust_id": sub["customer_id"],
                    "p_start": period.start,
                    "p_end": period.end,
                    "issue": issue_d,
                    "due": due_d,
                    "subtotal": priced.subtotal_minor,
                    "discount": priced.discount_minor,
                    "tax": priced.tax_minor,
                    "total": priced.total_minor,
                    "run_id": run_id,
                },
            ).fetchone()

            if not inv:
                # Lost race on conflict! Rollback savepoint to release claims
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                continue

            invoice_id = inv["id"]

            # Insert invoice lines
            for pl in priced.lines:
                conn.execute(
                    """
                    INSERT INTO invoice_lines (
                        invoice_id, description, product_id, variant_id,
                        quantity, unit_price_minor, line_subtotal_minor,
                        discount_minor, tax_rate_bps, tax_inclusive, tax_minor,
                        total_minor, calc_trace
                    ) VALUES (
                        %(inv_id)s, %(desc)s, %(prod_id)s, %(var_id)s,
                        %(qty)s, %(unit_price)s, %(subtotal)s,
                        %(discount)s, %(tax_bps)s, %(tax_inc)s, %(tax)s,
                        %(total)s, %(trace)s
                    )
                    """,
                    {
                        "inv_id": invoice_id,
                        "desc": pl.line.description,
                        "prod_id": pl.line.product_id,
                        "var_id": pl.line.variant_id,
                        "qty": pl.line.quantity,
                        "unit_price": pl.line.unit_price_minor,
                        "subtotal": pl.subtotal_minor,
                        "discount": pl.discount_minor,
                        "tax_bps": pl.line.tax_rate_bps,
                        "tax_inc": pl.line.tax_inclusive,
                        "tax": pl.tax_minor,
                        "total": pl.total_minor,
                        "trace": Jsonb(pl.calc_trace),
                    },
                )

            # Insert discount redemptions
            for disc_id, disc_amt in claimed_discounts:
                conn.execute(
                    """
                    INSERT INTO discount_redemptions (discount_id, invoice_id, amount_minor)
                    VALUES (%(disc_id)s, %(inv_id)s, %(amt)s)
                    """,
                    {"disc_id": disc_id, "inv_id": invoice_id, "amt": disc_amt},
                )

            # Auto confirm if requested
            if auto_confirm:
                # Generate invoice number: INV-<year>-<6 digits>
                seq_val = conn.execute("SELECT nextval('invoice_number_seq') as seq").fetchone()["seq"]
                inv_number = f"INV-{issue_d.year}-{seq_val:06d}"
                conn.execute(
                    """
                    UPDATE invoices
                       SET status = 'confirmed', number = %(num)s
                     WHERE id = %(id)s
                    """,
                    {"num": inv_number, "id": invoice_id},
                )

            # Write audit
            audit(
                conn,
                actor_id=actor_id,
                action="create_invoice",
                entity="invoice",
                entity_id=invoice_id,
                before=None,
                after={
                    "subscription_id": subscription_id,
                    "period_start": str(period.start),
                    "total_minor": priced.total_minor,
                    "status": "confirmed" if auto_confirm else "draft",
                },
            )

            conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            created_invoice_ids.append(invoice_id)
            existing_map[period.start] = "confirmed" if auto_confirm else "draft"

        except Exception as e:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            raise e

    return created_invoice_ids


def run_billing(
    as_of: date | None = None,
    mode: str = "live",
    actor_id: int | None = None,
    auto_confirm: bool = False,
    subscription_ids: list[int] | None = None,
) -> int:
    """Run billing over all candidates and return the billing_runs.id (§13.3).

    mode is 'dry' or 'live'. Records one billing_run_items row per candidate
    with a dominant disposition, plus the run counts and integrity summary.
    Dry mode runs the same code path and rolls each subscription back.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
