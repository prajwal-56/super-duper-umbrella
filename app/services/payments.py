"""Payment recording. Owner: D."""

from __future__ import annotations

import uuid
from datetime import date

import psycopg
from fastapi import HTTPException

from app.audit import audit


def record(
    conn: psycopg.Connection,
    invoice_id: int,
    method: str,
    amount_minor: int,
    paid_on: date,
    note: str | None,
    actor_id: int | None,
    idempotency_key: str | None = None,
) -> int:
    """Record a payment against a confirmed invoice (§13.6) and return its id.

    Locks the invoice row, rejects overpayment (422) and non-confirmed
    invoices, honors the idempotency key, sets the invoice paid when fully
    paid, and writes the audit row in the same transaction.
    """
    # Idempotency: return existing payment id if key already used
    if idempotency_key:
        existing = conn.execute(
            "SELECT id FROM payments WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        if existing:
            return int(existing["id"])

    # Lock the invoice row
    row = conn.execute(
        "SELECT id, status, total_minor, amount_paid_minor FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if row["status"] != "confirmed":
        raise HTTPException(
            status_code=422,
            detail=f"Payment requires a confirmed invoice (status={row['status']})",
        )

    outstanding = int(row["total_minor"]) - int(row["amount_paid_minor"])
    if amount_minor > outstanding:
        raise HTTPException(
            status_code=422,
            detail=f"Overpayment rejected: outstanding={outstanding}, attempted={amount_minor}",
        )
    if amount_minor <= 0:
        raise HTTPException(status_code=422, detail="Payment amount must be positive")

    key = idempotency_key or str(uuid.uuid4())
    pay_row = conn.execute(
        """
        INSERT INTO payments (invoice_id, method, amount_minor, paid_on, note, recorded_by, idempotency_key)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (invoice_id, method, amount_minor, paid_on, note, actor_id, key),
    ).fetchone()
    payment_id = int(pay_row["id"])

    new_paid = int(row["amount_paid_minor"]) + amount_minor
    new_status = "paid" if new_paid >= int(row["total_minor"]) else "confirmed"

    conn.execute(
        "UPDATE invoices SET amount_paid_minor = %s, status = %s WHERE id = %s",
        (new_paid, new_status, invoice_id),
    )
    audit(
        conn,
        actor_id,
        "payment.record",
        "invoice",
        invoice_id,
        before={"amount_paid_minor": int(row["amount_paid_minor"]), "status": "confirmed"},
        after={"amount_paid_minor": new_paid, "status": new_status},
    )
    return payment_id
