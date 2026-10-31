from datetime import date

from app import clock
from app.db import conn
from app.services.billing import bill_subscription, preview_next_invoice


def _subscription(c):
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Preview Co', 'preview@example.com') RETURNING id"
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
        VALUES ('Preview Seat', 'service', 20000, %(tax)s) RETURNING id
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
            %(cust)s, %(plan)s, '2026-01-01', '2026-06-30', %(pt)s, 'active'
        ) RETURNING id
        """,
        {"cust": cust["id"], "plan": plan["id"], "pt": terms["id"]},
    ).fetchone()
    sub_id = sub["id"]
    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor,
            tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (%(sub)s, %(prod)s, 2, 20000, %(tax)s, 1800, false)
        """,
        {"sub": sub_id, "prod": product["id"], "tax": tax["id"]},
    )
    discount = c.execute(
        """
        INSERT INTO discounts (
            name, kind, value, starts_on, ends_on, scope, usage_limit, auto_apply
        ) VALUES (
            'Preview discount', 'percent', 1000, '2026-01-01', '2026-12-31',
            'subscription', 1, true
        ) RETURNING id
        """
    ).fetchone()
    return sub_id, discount["id"]


def test_preview_matches_the_next_real_invoice_without_writing():
    clock.set_simulated(date(2026, 1, 15), None)
    with conn() as c:
        sub_id, discount_id = _subscription(c)

    with conn() as c:
        preview = preview_next_invoice(c, sub_id)
        assert preview is not None
        assert preview["period_start"] == date(2026, 1, 1)
        assert preview["period_end"] == date(2026, 1, 31)
        assert preview["total_minor"] == (
            preview["subtotal_minor"] - preview["discount_minor"] + preview["tax_minor"]
        )
        assert len(preview["lines"]) == 1
        assert preview["lines"][0]["calc_trace"]

        assert c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"] == 0
        usage = c.execute(
            "SELECT usage_count FROM discounts WHERE id = %(id)s",
            {"id": discount_id},
        ).fetchone()["usage_count"]
        assert usage == 0

        created = bill_subscription(c, sub_id, as_of=date(2026, 1, 15), actor_id=None)
        assert len(created) == 1
        invoice = c.execute(
            "SELECT * FROM invoices WHERE id = %(id)s", {"id": created[0]}
        ).fetchone()
        assert invoice["period_start"] == preview["period_start"]
        assert invoice["subtotal_minor"] == preview["subtotal_minor"]
        assert invoice["discount_minor"] == preview["discount_minor"]
        assert invoice["tax_minor"] == preview["tax_minor"]
        assert invoice["total_minor"] == preview["total_minor"]
        assert preview_next_invoice(c, sub_id) is None
