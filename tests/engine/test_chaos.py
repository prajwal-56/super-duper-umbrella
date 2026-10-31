from datetime import date

from app import clock
from app.db import conn
from app.services.chaos import hammer


def _subscription(c):
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Chaos Co', 'chaos@example.com') RETURNING id"
    ).fetchone()
    terms = c.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
    ).fetchone()
    tax = c.execute(
        "INSERT INTO taxes (name, rate_bps, inclusive) VALUES ('GST 18%', 1800, false) RETURNING id"
    ).fetchone()
    product = c.execute(
        """
        INSERT INTO products (name, type, sales_price_minor, tax_id)
        VALUES ('Chaos Seat', 'service', 20000, %(tax)s) RETURNING id
        """,
        {"tax": tax["id"]},
    ).fetchone()
    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, price_minor)
        VALUES ('Monthly', 'month', 1, 0) RETURNING id
        """
    ).fetchone()
    sub = c.execute(
        """
        INSERT INTO subscriptions (
            customer_id, plan_id, start_date, expiry_date, payment_term_id, status
        ) VALUES (
            %(cust)s, %(plan)s, '2026-01-01', '2026-12-31', %(pt)s, 'active'
        ) RETURNING id
        """,
        {"cust": cust["id"], "plan": plan["id"], "pt": terms["id"]},
    ).fetchone()
    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor,
            tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (%(sub)s, %(prod)s, 1, 20000, %(tax)s, 1800, false)
        """,
        {"sub": sub["id"], "prod": product["id"], "tax": tax["id"]},
    )
    return sub["id"]


def test_hammer_concurrent_rounds_create_no_duplicates():
    clock.set_simulated(date(2026, 10, 31), None)
    with conn() as c:
        sub_id = _subscription(c)

    result = hammer(workers=4, rounds=3, actor_id=None)

    assert result["created"] == 12
    assert result["duplicates"] == 0
    assert result["blocked_duplicates"] >= 0
    assert isinstance(result["invariants"], list)

    with conn() as c:
        invoices = c.execute(
            "SELECT COUNT(*) AS n FROM invoices WHERE subscription_id = %(id)s",
            {"id": sub_id},
        ).fetchone()["n"]
        assert invoices == 12
        duplicates = c.execute(
            """
            SELECT COUNT(*) AS n FROM (
                SELECT subscription_id, period_start
                  FROM invoices
                 WHERE status <> 'cancelled'
                 GROUP BY subscription_id, period_start
                HAVING COUNT(*) > 1
            ) AS dup
            """
        ).fetchone()["n"]
        assert duplicates == 0


def test_hammer_rejects_empty_runs():
    for workers, rounds in ((0, 1), (1, 0)):
        try:
            hammer(workers=workers, rounds=rounds, actor_id=None)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
