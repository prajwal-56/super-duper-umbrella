"""Invoice operations. Owner: D. Created as a contract stub by A."""

from __future__ import annotations

import psycopg


def confirm(conn: psycopg.Connection, invoice_id: int, actor_id: int | None) -> None:
    """Confirm a draft invoice: assign INV-<year>-<6 digits>, set the due date, audit."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D


def confirm_many(
    conn: psycopg.Connection, invoice_ids: list[int], actor_id: int | None
) -> int:
    """Confirm several invoices in one transaction; return the number confirmed."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D


def cancel(
    conn: psycopg.Connection, invoice_id: int, actor_id: int | None, reason: str
) -> None:
    """Cancel an invoice (blocked when payments exist); void redemptions, release usage."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D


def send(conn: psycopg.Connection, invoice_id: int, actor_id: int | None) -> None:
    """Queue the invoice email in the outbox (only confirmed invoices); set sent_at."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D


def get_for_customer(
    conn: psycopg.Connection, invoice_id: int, customer_id: int
) -> dict | None:
    """Return the invoice only when it belongs to customer_id, else None (portal 404)."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D
