"""Reports. Owner: D. Created as a contract stub by A."""

from __future__ import annotations

import psycopg


def dashboard(conn: psycopg.Connection, filters: dict) -> dict:
    """Return the dashboard figures for the filters: active count, MRR, collected,
    outstanding, overdue count and amount, plus revenue by month. Every figure
    must equal the total of the list it links to (INV-06).
    """
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D


def overdue(conn: psycopg.Connection, filters: dict, page: int, page_size: int) -> dict:
    """Paginated overdue invoices (D-07: confirmed, outstanding > 0, due before today)."""
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D
