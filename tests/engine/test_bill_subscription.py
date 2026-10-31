from datetime import date

from app.db import conn
from app.services.billing import bill_subscription


def setup_subscription_with_lines_and_discounts(c):
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Billing Test Co', 'test@example.com') RETURNING id"
    ).fetchone()
    cust_id = cust["id"]

    pt = c.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES ('Net 15', 15) RETURNING id"
    ).fetchone()
    pt_id = pt["id"]

    tax = c.execute(
        "INSERT INTO taxes (name, rate_bps, inclusive) VALUES ('GST 18%', 1800, false) RETURNING id"
    ).fetchone()
    tax_id = tax["id"]

    prod = c.execute(
        """
        INSERT INTO products (name, type, sales_price_minor, tax_id)
        VALUES ('Cloud Seat', 'service', 10000, %(tax_id)s)
        RETURNING id
        """,
        {"tax_id": tax_id},
    ).fetchone()
    prod_id = prod["id"]

    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, price_minor)
        VALUES ('Monthly Cloud', 'month', 1, 5000)
        RETURNING id
        """
    ).fetchone()
    plan_id = plan["id"]

    disc = c.execute(
        """
        INSERT INTO discounts (
            name, kind, value, starts_on, ends_on, scope, product_id, usage_limit, auto_apply
        ) VALUES (
            '10 pct OFF', 'percent', 1000, '2026-01-01', '2026-12-31', 'product', %(prod_id)s, 2, true
        ) RETURNING id
        """,
        {"prod_id": prod_id},
    ).fetchone()
    disc_id = disc["id"]

    sub = c.execute(
        """
        INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
        VALUES (%(cust_id)s, %(plan_id)s, '2026-01-01', '2026-03-31', %(pt_id)s, 'active')
        RETURNING id
        """,
        {"cust_id": cust_id, "plan_id": plan_id, "pt_id": pt_id},
    ).fetchone()
    sub_id = sub["id"]

    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (
            %(sub_id)s, %(prod_id)s, 2, 10000, %(tax_id)s, 1800, false
        )
        """,
        {"sub_id": sub_id, "prod_id": prod_id, "tax_id": tax_id},
    )

    return {
        "cust_id": cust_id,
        "sub_id": sub_id,
        "prod_id": prod_id,
        "disc_id": disc_id,
    }


def test_bill_subscription_idempotent_and_calc_trace():
    as_of = date(2026, 2, 1)

    with conn() as c:
        setup = setup_subscription_with_lines_and_discounts(c)
        sub_id = setup["sub_id"]
        disc_id = setup["disc_id"]

        # First run: Jan 1 and Feb 1 periods should be billed
        invoice_ids = bill_subscription(c, sub_id, as_of=as_of, actor_id=1, auto_confirm=True)
        assert len(invoice_ids) == 2

        # Check invoice details
        inv1 = c.execute("SELECT * FROM invoices WHERE id = %(id)s", {"id": invoice_ids[0]}).fetchone()
        assert inv1["period_start"] == date(2026, 1, 1)
        assert inv1["status"] == "confirmed"
        assert inv1["number"].startswith("INV-2026-")

        # Check calc_trace exists on lines
        lines = c.execute("SELECT * FROM invoice_lines WHERE invoice_id = %(id)s", {"id": invoice_ids[0]}).fetchall()
        assert len(lines) == 2  # Product line + Plan fee line
        for line in lines:
            assert len(line["calc_trace"]) > 0

        # Check discount claimed
        d_row = c.execute("SELECT usage_count FROM discounts WHERE id = %(id)s", {"id": disc_id}).fetchone()
        assert d_row["usage_count"] == 2  # Used on Jan and Feb invoices

        # Running again as of same date creates 0 new invoices (idempotent!)
        second_run_ids = bill_subscription(c, sub_id, as_of=as_of, actor_id=1)
        assert len(second_run_ids) == 0


def test_bill_subscription_discount_exhaustion():
    as_of = date(2026, 3, 1)

    with conn() as c:
        setup = setup_subscription_with_lines_and_discounts(c)
        sub_id = setup["sub_id"]
        disc_id = setup["disc_id"]

        # Usage limit is 2. Periods Jan, Feb, Mar are 3 periods.
        # Jan and Feb will claim the discount; Mar will find discount exhausted and bill without it.
        invoice_ids = bill_subscription(c, sub_id, as_of=as_of, actor_id=1)
        assert len(invoice_ids) == 3

        d_row = c.execute("SELECT usage_count FROM discounts WHERE id = %(id)s", {"id": disc_id}).fetchone()
        assert d_row["usage_count"] == 2

        redemptions = c.execute("SELECT * FROM discount_redemptions WHERE discount_id = %(id)s", {"id": disc_id}).fetchall()
        assert len(redemptions) == 2
