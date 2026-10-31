"""Read model for the customer portal (A).

Every query takes the customer id from the session and filters on it, so a
customer asking for another customer's row gets None and the route answers 404
(BUILD_PLAN §14). Writes never happen here.
"""

from __future__ import annotations

import psycopg


def subscriptions_for_customer(conn: psycopg.Connection, customer_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT s.id, s.number, s.status, s.is_paused, s.start_date, s.expiry_date,
               s.closed_on, p.name AS plan_name, p.billing_interval, p.interval_count
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.customer_id = %s
        ORDER BY s.id DESC
        """,
        (customer_id,),
    ).fetchall()


def subscription_for_customer(
    conn: psycopg.Connection, subscription_id: int, customer_id: int
) -> dict | None:
    return conn.execute(
        """
        SELECT s.id, s.number, s.status, s.is_paused, s.start_date, s.expiry_date,
               s.closed_on, s.close_reason, p.name AS plan_name, p.billing_interval,
               p.interval_count, p.allow_pause, p.allow_renew, p.allow_early_close
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.id = %s AND s.customer_id = %s
        """,
        (subscription_id, customer_id),
    ).fetchone()


def subscription_lines(conn: psycopg.Connection, subscription_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT id, description, quantity, unit_price_minor, line_subtotal_minor
        FROM subscription_lines WHERE subscription_id = %s ORDER BY id
        """,
        (subscription_id,),
    ).fetchall()


def invoices_for_customer(conn: psycopg.Connection, customer_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT id, number, status, period_start, period_end, issue_date, due_date,
               total_minor, amount_paid_minor, subscription_id
        FROM invoices
        WHERE customer_id = %s
        ORDER BY id DESC
        """,
        (customer_id,),
    ).fetchall()


def invoice_for_customer(
    conn: psycopg.Connection, invoice_id: int, customer_id: int
) -> dict | None:
    return conn.execute(
        """
        SELECT id, number, status, period_start, period_end, issue_date, due_date,
               subtotal_minor, discount_minor, tax_minor, total_minor,
               amount_paid_minor, subscription_id
        FROM invoices
        WHERE id = %s AND customer_id = %s
        """,
        (invoice_id, customer_id),
    ).fetchone()


def invoice_lines(conn: psycopg.Connection, invoice_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT id, description, quantity, unit_price_minor, line_subtotal_minor,
               discount_minor, tax_rate_bps, tax_minor, total_minor
        FROM invoice_lines WHERE invoice_id = %s ORDER BY id
        """,
        (invoice_id,),
    ).fetchall()


def profile(conn: psycopg.Connection, customer_id: int) -> dict | None:
    return conn.execute(
        "SELECT id, name, email, phone, address FROM customers WHERE id = %s",
        (customer_id,),
    ).fetchone()
