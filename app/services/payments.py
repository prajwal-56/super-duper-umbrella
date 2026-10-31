"""Payment recording. Owner: D. Created as a contract stub by A."""

from __future__ import annotations

from datetime import date

import psycopg


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
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D
