"""Billing engine entry points (database logic). Owner: B.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.audit import audit
from app.clock import now as clock_now
from app.clock import today
from app.db import conn as db_conn
from app.domain.periods import expected_periods
from app.domain.pricing import (
    DiscountInput,
    LineInput,
    price_invoice,
)
from app.services.invariants import run_all

_MAX_PERIODS_PER_RUN = 36
_PERIOD_SCAN_CAP = 10_000


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
        cap=_PERIOD_SCAN_CAP,
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

    # Oldest missing periods first; never more than 36 per subscription per run.
    missing_periods = [
        period
        for period in expected
        if not period.paused and period.start not in existing_map
    ][:_MAX_PERIODS_PER_RUN]

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

    for period in missing_periods:
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
            priced = price_invoice(pricing_lines, eligible_discounts, as_of=period.start)

            claimed_discounts: list[tuple[int, int]] = []
            retry_pricing = False

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

                if not res:
                    eligible_discounts = [
                        d for d in eligible_discounts if d.id != app_disc.discount_id
                    ]
                    retry_pricing = True
                    break
                else:
                    claimed_discounts.append((app_disc.discount_id, app_disc.amount_minor))

            if retry_pricing:
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
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                continue

            invoice_id = inv["id"]

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

            for disc_id, disc_amt in claimed_discounts:
                conn.execute(
                    """
                    INSERT INTO discount_redemptions (discount_id, invoice_id, amount_minor)
                    VALUES (%(disc_id)s, %(inv_id)s, %(amt)s)
                    """,
                    {"disc_id": disc_id, "inv_id": invoice_id, "amt": disc_amt},
                )

            if auto_confirm:
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


def _partition_periods(
    sub: dict[str, Any],
    pauses: list[tuple[date, date | None]],
    invoice_statuses: dict[date, str],
    as_of: date,
) -> tuple[list[Any], bool, bool]:
    """Return (missing periods, saw a pause, saw a cancelled period)."""
    expected = expected_periods(
        start=sub["start_date"],
        expiry=sub["expiry_date"],
        unit=sub["billing_interval"],
        count=sub["interval_count"],
        as_of=as_of,
        closed_on=sub["closed_on"],
        pauses=pauses,
        cap=_PERIOD_SCAN_CAP,
    )
    missing: list[Any] = []
    has_paused = False
    has_voided = False
    for period in expected:
        if period.paused:
            has_paused = True
            continue
        status = invoice_statuses.get(period.start)
        if status is None:
            missing.append(period)
        elif status == "cancelled":
            has_voided = True
    return missing, has_paused, has_voided


def _no_bill_disposition(has_voided: bool, has_paused: bool) -> tuple[str, str]:
    if has_voided:
        return "skipped_period_voided", "Cancelled invoice, re-issue manually"
    if has_paused:
        return "skipped_paused", "Period in pause window"
    return "up_to_date", "All periods up to date"


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
    if as_of is None:
        as_of = today()

    # 1. Insert billing_runs row in separate initial transaction
    with db_conn() as init_conn:
        run_row = init_conn.execute(
            """
            INSERT INTO billing_runs (mode, as_of, status, started_by)
            VALUES (%(mode)s, %(as_of)s, 'running', %(actor)s)
            RETURNING id
            """,
            {"mode": mode, "as_of": as_of, "actor": actor_id},
        ).fetchone()
        run_id = run_row["id"]

    # 2. Bulk load candidate subscriptions
    # Candidates = subscriptions with status 'active', OR status 'closed AND billing_complete = false'
    with db_conn() as read_conn:
        subs_query = """
            SELECT s.*, p.billing_interval, p.interval_count
              FROM subscriptions s
              JOIN plans p ON p.id = s.plan_id
             WHERE (s.status = 'active' OR (s.status = 'closed' AND s.billing_complete = false))
               AND (%(sub_ids)s::bigint[] IS NULL OR s.id = ANY(%(sub_ids)s))
             ORDER BY s.id
        """
        candidate_subs = read_conn.execute(
            subs_query, {"sub_ids": subscription_ids}
        ).fetchall()

        if not candidate_subs:
            with db_conn() as fin_conn:
                fin_conn.execute(
                    """
                    UPDATE billing_runs
                       SET status = 'completed', finished_at = %(finished)s,
                           considered = 0, invoices_created = 0, amount_minor = 0
                     WHERE id = %(id)s
                    """,
                    {"id": run_id, "finished": clock_now()},
                )
            return run_id

        cand_ids = [s["id"] for s in candidate_subs]

        # Bulk load pauses
        all_pauses = read_conn.execute(
            """
            SELECT subscription_id, paused_on, resumed_on
              FROM subscription_pauses
             WHERE subscription_id = ANY(%(ids)s)
             ORDER BY paused_on
            """,
            {"ids": cand_ids},
        ).fetchall()
        pauses_by_sub: dict[int, list[tuple[date, date | None]]] = {}
        for p in all_pauses:
            pauses_by_sub.setdefault(p["subscription_id"], []).append(
                (p["paused_on"], p["resumed_on"])
            )

        # Bulk load existing invoices
        all_existing = read_conn.execute(
            """
            SELECT subscription_id, period_start, status
              FROM invoices
             WHERE subscription_id = ANY(%(ids)s)
            """,
            {"ids": cand_ids},
        ).fetchall()
        invoices_by_sub: dict[int, dict[date, str]] = {}
        for inv in all_existing:
            invoices_by_sub.setdefault(inv["subscription_id"], {})[inv["period_start"]] = inv["status"]

    total_invoices_created = 0
    total_amount_minor = 0
    blocked_duplicates_count = 0

    items_to_insert: list[dict[str, Any]] = []
    deferred_candidates: list[dict[str, Any]] = []

    # Helper to process one candidate
    def process_candidate(sub: dict[str, Any]) -> dict[str, Any]:
        nonlocal total_invoices_created, total_amount_minor, blocked_duplicates_count
        sub_id = sub["id"]
        sub_pauses = pauses_by_sub.get(sub_id, [])
        sub_invs = invoices_by_sub.get(sub_id, {})

        # Compute expected periods
        missing, has_paused, has_voided = _partition_periods(
            sub, sub_pauses, sub_invs, as_of
        )

        if not missing:
            disp, reason = _no_bill_disposition(has_voided, has_paused)

            # If closed and nothing missing -> mark billing_complete
            if sub["status"] == "closed":
                with db_conn() as close_conn:
                    close_conn.execute(
                        "UPDATE subscriptions SET billing_complete = true WHERE id = %(id)s",
                        {"id": sub_id},
                    )

            return {
                "subscription_id": sub_id,
                "disposition": disp,
                "periods_billed": 0,
                "invoice_ids": [],
                "reason": reason,
                "error": None,
            }

        # Sub needs billing -> open own transaction with SKIP LOCKED
        try:
            created_ids: list[int] = []
            billed_amount = 0
            missing_under_lock: list[Any] = []
            has_paused_lock = has_paused
            has_voided_lock = has_voided
            try:
                with db_conn() as sub_conn:
                    locked = sub_conn.execute(
                        "SELECT id FROM subscriptions WHERE id = %(id)s FOR UPDATE SKIP LOCKED",
                        {"id": sub_id},
                    ).fetchone()

                    if not locked:
                        return {
                            "subscription_id": sub_id,
                            "disposition": "deferred_locked",
                            "periods_billed": 0,
                            "invoice_ids": [],
                            "reason": "Locked by concurrent process",
                            "error": None,
                        }

                    fresh_rows = sub_conn.execute(
                        "SELECT period_start, status FROM invoices WHERE subscription_id = %(id)s",
                        {"id": sub_id},
                    ).fetchall()
                    fresh_map = {row["period_start"]: row["status"] for row in fresh_rows}
                    missing_under_lock, has_paused_lock, has_voided_lock = (
                        _partition_periods(sub, sub_pauses, fresh_map, as_of)
                    )

                    if not missing_under_lock:
                        if sub["status"] == "closed":
                            sub_conn.execute(
                                "UPDATE subscriptions SET billing_complete = true WHERE id = %(id)s",
                                {"id": sub_id},
                            )
                        disp, reason = _no_bill_disposition(
                            has_voided_lock, has_paused_lock
                        )
                        return {
                            "subscription_id": sub_id,
                            "disposition": disp,
                            "periods_billed": 0,
                            "invoice_ids": [],
                            "reason": reason,
                            "error": None,
                        }

                    created_ids = bill_subscription(
                        sub_conn,
                        sub_id,
                        as_of=as_of,
                        actor_id=actor_id,
                        run_id=run_id,
                        auto_confirm=auto_confirm,
                    )
                    if created_ids:
                        amount_row = sub_conn.execute(
                            "SELECT COALESCE(SUM(total_minor), 0) AS total FROM invoices WHERE id = ANY(%(ids)s)",
                            {"ids": created_ids},
                        ).fetchone()
                        billed_amount = amount_row["total"]

                    if mode == "dry":
                        raise psycopg.Rollback()

                    if (
                        sub["status"] == "closed"
                        and len(created_ids) == len(missing_under_lock)
                    ):
                        sub_conn.execute(
                            "UPDATE subscriptions SET billing_complete = true WHERE id = %(id)s",
                            {"id": sub_id},
                        )
            except psycopg.Rollback:
                pass

            total_invoices_created += len(created_ids)
            total_amount_minor += billed_amount
            if mode == "live":
                to_bill = missing_under_lock[:_MAX_PERIODS_PER_RUN]
                blocked_duplicates_count += max(0, len(to_bill) - len(created_ids))

            if created_ids:
                verb = "Dry-run: would bill" if mode == "dry" else "Billed"
                disp = "billed"
                reason = f"{verb} {len(created_ids)} period(s)"
            else:
                disp, reason = _no_bill_disposition(has_voided_lock, has_paused_lock)

            return {
                "subscription_id": sub_id,
                "disposition": disp,
                "periods_billed": len(created_ids),
                "invoice_ids": created_ids,
                "reason": reason,
                "error": None,
            }

        except Exception as exc:
            return {
                "subscription_id": sub_id,
                "disposition": "failed",
                "periods_billed": 0,
                "invoice_ids": [],
                "reason": "Exception during billing",
                "error": str(exc),
            }

    # Pass 1: process all candidates
    for sub in candidate_subs:
        item = process_candidate(sub)
        if item["disposition"] == "deferred_locked":
            deferred_candidates.append(sub)
        else:
            items_to_insert.append(item)

    # Pass 2: retry deferred candidates once
    for sub in deferred_candidates:
        item = process_candidate(sub)
        items_to_insert.append(item)

    # Final transaction: write billing_run_items and update billing_runs
    with db_conn() as fin_conn:
        for item in items_to_insert:
            fin_conn.execute(
                """
                INSERT INTO billing_run_items (
                    run_id, subscription_id, disposition, periods_billed,
                    invoice_ids, reason, error
                ) VALUES (
                    %(run_id)s, %(sub_id)s, %(disp)s, %(periods)s,
                    %(inv_ids)s, %(reason)s, %(err)s
                )
                """,
                {
                    "run_id": run_id,
                    "sub_id": item["subscription_id"],
                    "disp": item["disposition"],
                    "periods": item["periods_billed"],
                    "inv_ids": item["invoice_ids"],
                    "reason": item["reason"],
                    "err": item["error"],
                },
            )

        # Integrity summary (INV-01..08)
        integrity_summary: dict[str, Any] = {}
        try:
            inv_results = run_all(fin_conn)
        except NotImplementedError:
            inv_results = []
        integrity_summary = {
            r.id: {"ok": r.ok, "violations": r.violations} for r in inv_results
        }

        fin_conn.execute(
            """
            UPDATE billing_runs
               SET status = 'completed', finished_at = %(finished)s,
                   considered = %(considered)s,
                   invoices_created = %(created)s,
                   amount_minor = %(amount)s,
                   blocked_duplicates = %(blocked)s,
                   integrity_summary = %(summary)s
             WHERE id = %(id)s
            """,
            {
                "id": run_id,
                "finished": clock_now(),
                "considered": len(items_to_insert),
                "created": total_invoices_created,
                "amount": total_amount_minor,
                "blocked": blocked_duplicates_count,
                "summary": Jsonb(integrity_summary) if integrity_summary else None,
            },
        )

    return run_id
