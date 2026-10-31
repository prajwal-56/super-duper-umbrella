"""Invoice operations. Owner: D."""

from __future__ import annotations

import psycopg

from app.audit import audit
from app.outbox import queue_email


def confirm(conn: psycopg.Connection, invoice_id: int, actor_id: int | None) -> None:
    """Confirm a draft invoice: assign INV-<year>-<6 digits>, set due date, audit."""
    row = conn.execute(
        """
        SELECT i.id, i.status, i.issue_date, i.subscription_id,
               pt.due_days,
               i.total_minor, i.subtotal_minor, i.discount_minor, i.tax_minor
        FROM invoices i
        JOIN subscriptions s ON s.id = i.subscription_id
        JOIN payment_terms pt ON pt.id = s.payment_term_id
        WHERE i.id = %s
        FOR UPDATE
        """,
        (invoice_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Invoice {invoice_id} not found")
    if row["status"] != "draft":
        raise ValueError(f"Invoice {invoice_id} is {row['status']}, expected draft")

    issue_date = row["issue_date"]
    due_date = issue_date + __import__("datetime").timedelta(days=int(row["due_days"]))
    year = issue_date.year

    # Assign a sequence number atomically
    seq_row = conn.execute(
        "SELECT nextval('invoice_number_seq') AS n"
    ).fetchone()
    number = f"INV-{year}-{int(seq_row['n']):06d}"

    conn.execute(
        """
        UPDATE invoices
        SET status = 'confirmed', number = %s, due_date = %s
        WHERE id = %s
        """,
        (number, due_date, invoice_id),
    )
    audit(
        conn,
        actor_id,
        "invoice.confirm",
        "invoice",
        invoice_id,
        before={"status": "draft"},
        after={"status": "confirmed", "number": number, "due_date": str(due_date)},
    )


def confirm_many(
    conn: psycopg.Connection, invoice_ids: list[int], actor_id: int | None
) -> int:
    """Confirm several invoices in one transaction; return the number confirmed."""
    confirmed = 0
    for iid in invoice_ids:
        try:
            confirm(conn, iid, actor_id)
            confirmed += 1
        except ValueError:
            pass
    return confirmed


def cancel(
    conn: psycopg.Connection, invoice_id: int, actor_id: int | None, reason: str
) -> None:
    """Cancel an invoice (blocked when payments exist); void redemptions, release usage."""
    row = conn.execute(
        "SELECT id, status FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Invoice {invoice_id} not found")
    if row["status"] == "cancelled":
        return
    if row["status"] not in ("draft", "confirmed"):
        raise ValueError(f"Cannot cancel invoice in status {row['status']}")

    # Block if any payments exist
    pay_count = conn.execute(
        "SELECT COUNT(*) AS cnt FROM payments WHERE invoice_id = %s",
        (invoice_id,),
    ).fetchone()["cnt"]
    if pay_count > 0:
        raise ValueError("Cannot cancel an invoice that has payments")

    # Void redemptions and decrement usage counters
    redemptions = conn.execute(
        """
        SELECT id, discount_id FROM discount_redemptions
        WHERE invoice_id = %s AND voided_at IS NULL
        """,
        (invoice_id,),
    ).fetchall()
    for r in redemptions:
        conn.execute(
            "UPDATE discount_redemptions SET voided_at = now() WHERE id = %s",
            (r["id"],),
        )
        conn.execute(
            "UPDATE discounts SET usage_count = GREATEST(0, usage_count - 1) WHERE id = %s",
            (r["discount_id"],),
        )

    conn.execute(
        "UPDATE invoices SET status = 'cancelled' WHERE id = %s",
        (invoice_id,),
    )
    audit(
        conn,
        actor_id,
        "invoice.cancel",
        "invoice",
        invoice_id,
        before={"status": row["status"]},
        after={"status": "cancelled", "reason": reason},
    )


def send(conn: psycopg.Connection, invoice_id: int, actor_id: int | None) -> None:
    """Queue the invoice email in the outbox (only confirmed invoices); set sent_at."""
    row = conn.execute(
        """
        SELECT i.id, i.status, i.number, i.total_minor, i.due_date,
               c.email AS customer_email, c.name AS customer_name
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.id = %s
        FOR UPDATE
        """,
        (invoice_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Invoice {invoice_id} not found")
    if row["status"] != "confirmed":
        raise ValueError(f"Only confirmed invoices can be sent (status={row['status']})")

    from app.money import fmt

    subject = f"Invoice {row['number']} from Brightloop — due {row['due_date']}"
    body_html = (
        f"<p>Dear {row['customer_name']},</p>"
        f"<p>Please find your invoice <strong>{row['number']}</strong> "
        f"for <strong>{fmt(row['total_minor'])}</strong> due on "
        f"<strong>{row['due_date']}</strong> attached.</p>"
        f"<p>Thank you,<br>Brightloop Software</p>"
    )
    queue_email(
        conn,
        kind="invoice",
        to_email=row["customer_email"] or "",
        subject=subject,
        body_html=body_html,
        link=f"/app/invoices/{invoice_id}",
    )
    conn.execute(
        "UPDATE invoices SET sent_at = now() WHERE id = %s",
        (invoice_id,),
    )
    audit(conn, actor_id, "invoice.send", "invoice", invoice_id)


def get_for_customer(
    conn: psycopg.Connection, invoice_id: int, customer_id: int
) -> dict | None:
    """Return the invoice only when it belongs to customer_id, else None (portal 404)."""
    row = conn.execute(
        "SELECT * FROM invoices WHERE id = %s AND customer_id = %s",
        (invoice_id, customer_id),
    ).fetchone()
    return dict(row) if row else None


def list_invoices(
    conn: psycopg.Connection,
    *,
    customer_id: int | None = None,
    subscription_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Return paginated invoice list with filters."""
    wheres = []
    params: list = []

    if customer_id is not None:
        wheres.append("i.customer_id = %s")
        params.append(customer_id)
    if subscription_id is not None:
        wheres.append("i.subscription_id = %s")
        params.append(subscription_id)
    if status:
        wheres.append("i.status = %s")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    offset = (page - 1) * page_size

    total_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM invoices i {where_sql}",
        params,
    ).fetchone()
    total = int(total_row["cnt"])

    rows = conn.execute(
        f"""
        SELECT i.id, i.number, i.status, i.period_start, i.period_end,
               i.issue_date, i.due_date, i.total_minor, i.amount_paid_minor,
               i.subtotal_minor, i.discount_minor, i.tax_minor,
               i.subscription_id, i.customer_id, i.sent_at,
               c.name AS customer_name, s.number AS sub_number
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        JOIN subscriptions s ON s.id = i.subscription_id
        {where_sql}
        ORDER BY i.issue_date DESC, i.id DESC
        LIMIT %s OFFSET %s
        """,
        params + [page_size, offset],
    ).fetchall()

    return {
        "invoices": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
    }


def get_invoice(conn: psycopg.Connection, invoice_id: int) -> dict | None:
    """Return invoice with its lines."""
    row = conn.execute(
        """
        SELECT i.*, c.name AS customer_name, c.email AS customer_email,
               c.address AS customer_address, s.number AS sub_number
        FROM invoices i
        JOIN customers c ON c.id = i.customer_id
        JOIN subscriptions s ON s.id = i.subscription_id
        WHERE i.id = %s
        """,
        (invoice_id,),
    ).fetchone()
    if row is None:
        return None
    inv = dict(row)
    lines = conn.execute(
        "SELECT * FROM invoice_lines WHERE invoice_id = %s ORDER BY id",
        (invoice_id,),
    ).fetchall()
    inv["lines"] = [dict(line) for line in lines]
    payments = conn.execute(
        "SELECT * FROM payments WHERE invoice_id = %s ORDER BY paid_on, id",
        (invoice_id,),
    ).fetchall()
    inv["payments"] = [dict(p) for p in payments]
    return inv
