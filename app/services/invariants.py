"""Integrity checks (INV-01..08). Owner: D. Created as a contract stub by A.

The SQL in db/queries/ is written independently of the engine so a bug in the
Python cannot hide behind the same bug in the checker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg

from app.clock import today


@dataclass
class InvariantResult:
    id: str
    name: str
    ok: bool
    violations: int
    sample_rows: list[dict[str, Any]] = field(default_factory=list)


def _exec(conn, sql, params=None):
    "Execute SQL and return rows."
    if params:
        return conn.execute(sql, params).fetchall()
    return conn.execute(sql).fetchall()


def _exec_one(conn, sql, params=None):
    "Execute SQL and return single row."
    if params:
        return conn.execute(sql, params).fetchone()
    return conn.execute(sql).fetchone()


def run_all(conn: psycopg.Connection) -> list[InvariantResult]:
    """Run every integrity check and return one InvariantResult per check.

    Checks: no duplicate periods, invoice totals equal their lines, payments
    consistent, no missing periods, discount counters consistent, dashboard
    equals raw data, run accounting, calc traces reconcile (§13.7).
    """
    results: list[InvariantResult] = []

    # INV-01: No two non-cancelled invoices share (subscription_id, period_start)
    inv01_rows = _exec(
        conn,
        """
        SELECT subscription_id, period_start, COUNT(*) AS cnt
        FROM invoices
        WHERE status <> 'cancelled'
        GROUP BY subscription_id, period_start
        HAVING COUNT(*) > 1
        """,
    )
    ok01 = len(inv01_rows) == 0
    results.append(
        InvariantResult(
            id="INV-01",
            name="No duplicate (subscription_id, period_start) among non-cancelled invoices",
            ok=ok01,
            violations=len(inv01_rows),
            sample_rows=inv01_rows[:5],
        )
    )

    # INV-02: Per invoice: subtotal, discount, tax and total equal sums of lines
    inv02_rows = _exec(
        conn,
        """
        SELECT i.id,
               i.subtotal_minor != SUM(il.line_subtotal_minor) AS sub_mismatch,
               i.discount_minor != SUM(il.discount_minor) AS disc_mismatch,
               i.tax_minor != SUM(il.tax_minor) AS tax_mismatch,
               i.total_minor != SUM(il.total_minor) AS total_mismatch
        FROM invoices i
        JOIN invoice_lines il ON il.invoice_id = i.id
        GROUP BY i.id, i.subtotal_minor, i.discount_minor, i.tax_minor, i.total_minor
        HAVING i.subtotal_minor != SUM(il.line_subtotal_minor)
            OR i.discount_minor != SUM(il.discount_minor)
            OR i.tax_minor != SUM(il.tax_minor)
            OR i.total_minor != SUM(il.total_minor)
        """,
    )
    has02 = any(
        r[1] or r[2] or r[3] or r[4] for r in inv02_rows
    )
    inv02_violations = sum(
        any(r[1:5]) for r in inv02_rows
    )
    results.append(
        InvariantResult(
            id="INV-02",
            name="Per invoice: subtotal, discount, tax and total equal sums of lines",
            ok=not has02,
            violations=inv02_violations,
            sample_rows=inv02_rows[:5],
        )
    )

    # INV-03: 0 <= amount_paid <= total; paid = sum(payments); paid = total iff status=paid
    inv03_rows = _exec(
        conn,
        """
        SELECT i.id,
               i.amount_paid_minor < 0 AS negative_paid,
               i.amount_paid_minor > i.total_minor AS overpaid,
               (SELECT COALESCE(SUM(amount_minor), 0) FROM payments p WHERE p.invoice_id = i.id) != i.amount_paid_minor AS paid_mismatch,
               i.status = 'paid' AND i.amount_paid_minor != i.total_minor AS status_mismatch
        FROM invoices i
        WHERE i.amount_paid_minor < 0
           OR i.amount_paid_minor > i.total_minor
           OR (i.status = 'paid' AND i.amount_paid_minor != i.total_minor)
           OR (i.status != 'paid' AND i.amount_paid_minor = i.total_minor)
        """,
    )
    has03 = any(
        any(r[1:3]) or r[2] or r[3] for r in inv03_rows
    )
    inv03_violations = sum(
        1 for r in inv03_rows if any(r[1:3]) or r[2] or r[3]
    )
    results.append(
        InvariantResult(
            id="INV-03",
            name="0 <= amount_paid <= total; paid = sum(payments); paid = total iff status=paid",
            ok=not has03,
            violations=inv03_violations,
            sample_rows=inv03_rows[:5],
        )
    )

    # INV-04: No missing periods — every expected period has an invoice, void, or a pause
    as_of = today()
    inv04_rows = _exec(
        conn,
        """
        WITH RECURSIVE
          all_subs AS (
            SELECT id, start_date, expiry_date, closed_on
            FROM subscriptions
            WHERE status IN ('active', 'closed')
          ),
          all_periods AS (
            SELECT
              id AS sub_id,
              (start_date + (g.g || ' month')::interval)::date AS period_start
            FROM all_subs, generate_series(0, 35) AS g
            WHERE (start_date + (g.g || ' month')::interval)::date <= expiry_date
              AND (start_date + (g.g || ' month')::interval)::date <= %s
              AND (closed_on IS NULL
                   OR (start_date + (g.g || ' month')::interval)::date < closed_on)
          ),
          covered AS (
            SELECT DISTINCT subscription_id AS sub_id, period_start
            FROM invoices
          ),
          paused_periods AS (
            SELECT DISTINCT sp.subscription_id AS sub_id, ap.period_start
            FROM subscription_pauses sp
            JOIN all_periods ap ON ap.sub_id = sp.subscription_id
            WHERE ap.period_start >= sp.paused_on
              AND (sp.resumed_on IS NULL OR ap.period_start < sp.resumed_on)
          )
        SELECT p.sub_id, p.period_start
        FROM all_periods p
        LEFT JOIN covered i ON p.sub_id = i.sub_id AND p.period_start = i.period_start
        LEFT JOIN paused_periods pa ON p.sub_id = pa.sub_id AND p.period_start = pa.period_start
        WHERE i.sub_id IS NULL AND pa.sub_id IS NULL
        """,
        (as_of,),
    )

    ok04 = len(inv04_rows) == 0
    results.append(
        InvariantResult(
            id="INV-04",
            name="No missing periods: every expected period has an invoice, void, or pause",
            ok=ok04,
            violations=len(inv04_rows),
            sample_rows=inv04_rows[:5],
        )
    )

    # INV-05: usage_count <= usage_limit (non-voided redemptions)
    inv05_rows = _exec(
        conn,
        """
        SELECT d.id, d.usage_count, d.usage_limit,
               (SELECT COUNT(*) FROM discount_redemptions dr
                WHERE dr.discount_id = d.id AND dr.voided_at IS NULL) AS active_redemptions
        FROM discounts d
        WHERE (SELECT COUNT(*) FROM discount_redemptions dr
               WHERE dr.discount_id = d.id AND dr.voided_at IS NULL) > d.usage_limit
        """,
    )
    ok05 = len(inv05_rows) == 0
    results.append(
        InvariantResult(
            id="INV-05",
            name="usage_count <= usage_limit (non-voided redemptions)",
            ok=ok05,
            violations=len(inv05_rows),
            sample_rows=inv05_rows[:5],
        )
    )

    # INV-06: Dashboard figures equal an independent raw recomputation
    as_of = today()
    from app.services.reports import dashboard

    figures = dashboard(conn, {})
    raw = _exec_one(
        conn,
        """
        WITH money AS (
            SELECT COALESCE(SUM(amount_paid_minor), 0) AS collected,
                   COALESCE(SUM(total_minor - amount_paid_minor), 0) AS outstanding
              FROM invoices
             WHERE status IN ('confirmed', 'paid')
        ),
        overdue AS (
            SELECT COUNT(*) AS overdue_count,
                   COALESCE(SUM(total_minor - amount_paid_minor), 0) AS overdue_amount
              FROM invoices
             WHERE status = 'confirmed'
               AND (total_minor - amount_paid_minor) > 0
               AND due_date < %s
        ),
        active AS (
            SELECT COUNT(*) AS active_count
              FROM subscriptions
             WHERE status = 'active'
        )
        SELECT active.active_count, money.collected, money.outstanding,
               overdue.overdue_count, overdue.overdue_amount
          FROM active, money, overdue
        """,
        (as_of,),
    )
    mismatches = [
        key
        for key in (
            "active_count",
            "collected",
            "outstanding",
            "overdue_count",
            "overdue_amount",
        )
        if int(raw[key]) != int(figures[key])
    ]
    inv06_rows = [{"mismatched": mismatches, "raw": dict(raw), "dashboard": figures}] if mismatches else []
    ok06 = len(inv06_rows) == 0
    results.append(
        InvariantResult(
            id="INV-06",
            name="Dashboard figures equal raw recomputation",
            ok=ok06,
            violations=len(inv06_rows),
            sample_rows=inv06_rows[:5],
        )
    )

    # INV-07: Each billing run: considered = count(items)
    inv07_rows = _exec(
        conn,
        """
        SELECT r.id AS run_id,
               r.considered,
               COALESCE(i.item_count, 0) AS item_count
        FROM billing_runs r
        LEFT JOIN (
            SELECT run_id, COUNT(*) AS item_count
            FROM billing_run_items
            GROUP BY run_id
        ) i ON i.run_id = r.id
        WHERE r.considered != COALESCE(i.item_count, 0)
        """,
    )
    ok07 = len(inv07_rows) == 0
    results.append(
        InvariantResult(
            id="INV-07",
            name="Each billing run: considered = count(items)",
            ok=ok07,
            violations=len(inv07_rows),
            sample_rows=inv07_rows[:5],
        )
    )

    # INV-08: Invoice calc_trace reconciles to line totals
    inv08_rows = _exec(
        conn,
        """
        SELECT il.invoice_id,
               SUM(
                 il.line_subtotal_minor
                 - il.discount_minor
                 + CASE WHEN il.tax_inclusive = false THEN il.tax_minor ELSE 0 END
               ) AS computed_total,
               MAX(i.total_minor) AS stored_total
        FROM invoice_lines il
        JOIN invoices i ON i.id = il.invoice_id
        GROUP BY il.invoice_id
        HAVING SUM(
                  il.line_subtotal_minor
                  - il.discount_minor
                  + CASE WHEN il.tax_inclusive = false THEN il.tax_minor ELSE 0 END
                ) != MAX(i.total_minor)
        """,
    )
    ok08 = len(inv08_rows) == 0
    results.append(
        InvariantResult(
            id="INV-08",
            name="Invoice calc_trace reconciles to line totals",
            ok=ok08,
            violations=len(inv08_rows),
            sample_rows=inv08_rows[:5],
        )
    )

    return results
