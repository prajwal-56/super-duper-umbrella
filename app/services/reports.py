"""Reports and dashboard. Owner: D."""

from __future__ import annotations

import psycopg

from app.clock import today


def dashboard(conn: psycopg.Connection, filters: dict) -> dict:
    """Return dashboard figures: active subs count, MRR, collected, outstanding,
    overdue count/amount, plus revenue_by_month. Every figure must equal the
    total of the list it links to (INV-06).
    """
    as_of = today()

    # Active subscription count
    active_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM subscriptions WHERE status = 'active'"
    ).fetchone()
    active_count = int(active_row["cnt"])

    # MRR — pre-tax, non-paused Active subscriptions normalised to monthly (D-23)
    mrr_rows = conn.execute(
        """
        SELECT s.id,
               p.billing_interval,
               p.interval_count,
               COALESCE(SUM(sl.unit_price_minor * sl.quantity), 0) AS line_total
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        JOIN subscription_lines sl ON sl.subscription_id = s.id
        WHERE s.status = 'active' AND s.is_paused = false
        GROUP BY s.id, p.billing_interval, p.interval_count
        """
    ).fetchall()
    mrr = 0
    for r in mrr_rows:
        interval = r["billing_interval"]
        count = int(r["interval_count"])
        total = int(r["line_total"])
        if interval == "day":
            mrr += total * 365 // (12 * count)
        elif interval == "week":
            mrr += total * 52 // (12 * count)
        elif interval == "month":
            mrr += total // count
        elif interval == "year":
            mrr += total // (12 * count)

    # Collected, outstanding
    money_row = conn.execute(
        """
        SELECT
            COALESCE(SUM(amount_paid_minor), 0) AS collected,
            COALESCE(SUM(total_minor - amount_paid_minor), 0) AS outstanding
        FROM invoices
        WHERE status IN ('confirmed', 'paid')
        """
    ).fetchone()
    collected = int(money_row["collected"])
    outstanding = int(money_row["outstanding"])

    # Overdue: confirmed, unpaid, past due date
    overdue_row = conn.execute(
        """
        SELECT
            COUNT(*) AS cnt,
            COALESCE(SUM(total_minor - amount_paid_minor), 0) AS amount
        FROM invoices
        WHERE status = 'confirmed'
          AND (total_minor - amount_paid_minor) > 0
          AND due_date < %s
        """,
        (as_of,),
    ).fetchone()
    overdue_count = int(overdue_row["cnt"])
    overdue_amount = int(overdue_row["amount"])

    # Aging buckets: 0-30, 31-60, 61-90, 90+ days overdue
    aging_rows = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE %s - due_date <= 30) AS "0-30",
            COUNT(*) FILTER (WHERE %s - due_date BETWEEN 31 AND 60) AS "31-60",
            COUNT(*) FILTER (WHERE %s - due_date BETWEEN 61 AND 90) AS "61-90",
            COUNT(*) FILTER (WHERE %s - due_date > 90) AS "90+"
        FROM invoices
        WHERE status = 'confirmed'
          AND (total_minor - amount_paid_minor) > 0
          AND due_date < %s
        """,
        (as_of, as_of, as_of, as_of, as_of),
    ).fetchone()
    aging_0_30 = int(aging_rows["0-30"])
    aging_31_60 = int(aging_rows["31-60"])
    aging_61_90 = int(aging_rows["61-90"])
    aging_90plus = int(aging_rows["90+"])

    # Revenue by month (last 12 months of confirmed/paid invoices)
    rev_rows = conn.execute(
        """
        SELECT to_char(issue_date, 'YYYY-MM') AS month,
               SUM(total_minor) AS revenue
        FROM invoices
        WHERE status IN ('confirmed', 'paid')
          AND issue_date >= (date_trunc('month', %s::date) - interval '11 months')
        GROUP BY month
        ORDER BY month
        """,
        (as_of,),
    ).fetchall()
    revenue_by_month = [{"month": r["month"], "revenue": int(r["revenue"])} for r in rev_rows]

    return {
        "active_count": active_count,
        "mrr": mrr,
        "collected": collected,
        "outstanding": outstanding,
        "overdue_count": overdue_count,
        "overdue_amount": overdue_amount,
        "aging_0_30": aging_0_30,
        "aging_31_60": aging_31_60,
        "aging_61_90": aging_61_90,
        "aging_90plus": aging_90plus,
        "revenue_by_month": revenue_by_month,
        "as_of": as_of,
    }


def overdue(conn: psycopg.Connection, filters: dict, page: int, page_size: int) -> dict:
    """Paginated overdue invoices (confirmed, outstanding > 0, due before today)."""
    as_of = today()
    offset = (page - 1) * page_size

    wheres = [
        "i.status = 'confirmed'",
        "(i.total_minor - i.amount_paid_minor) > 0",
        "i.due_date < %s",
    ]
    params: list = [as_of]

    if filters.get("customer_id"):
        wheres.append("i.customer_id = %s")
        params.append(int(filters["customer_id"]))

    where_sql = "WHERE " + " AND ".join(wheres)

    total_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM invoices i {where_sql}",
        params,
    ).fetchone()
    total = int(total_row["cnt"])

    rows = conn.execute(
        f"""
        SELECT i.id, i.number, i.status, i.issue_date, i.due_date,
               i.total_minor, i.amount_paid_minor,
               (i.total_minor - i.amount_paid_minor) AS outstanding_minor,
               (%s::date - i.due_date) AS days_overdue,
               c.name AS customer_name, c.email AS customer_email,
               s.number AS sub_number
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        JOIN subscriptions s ON s.id = i.subscription_id
        {where_sql}
        ORDER BY i.due_date ASC, i.id
        LIMIT %s OFFSET %s
        """,
        [as_of] + params + [page_size, offset],
    ).fetchall()

    return {
        "invoices": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
        "as_of": as_of,
    }
