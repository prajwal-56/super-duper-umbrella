from datetime import date

from app.db import conn
from app.services.billing import run_billing


def setup_candidate_subscriptions(c):
    user = c.execute(
        "INSERT INTO users (email, password_hash, role) VALUES ('admin@example.com', 'hash', 'admin') RETURNING id"
    ).fetchone()
    user_id = user["id"]

    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Run Billing Co', 'rb@example.com') RETURNING id"
    ).fetchone()
    cust_id = cust["id"]

    pt = c.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
    ).fetchone()
    pt_id = pt["id"]

    tax = c.execute(
        "INSERT INTO taxes (name, rate_bps, inclusive) VALUES ('GST 18%', 1800, false) RETURNING id"
    ).fetchone()
    tax_id = tax["id"]

    prod = c.execute(
        """
        INSERT INTO products (name, type, sales_price_minor, tax_id)
        VALUES ('App License', 'service', 20000, %(tax_id)s)
        RETURNING id
        """,
        {"tax_id": tax_id},
    ).fetchone()
    prod_id = prod["id"]

    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, price_minor)
        VALUES ('Monthly Plan', 'month', 1, 0)
        RETURNING id
        """
    ).fetchone()
    plan_id = plan["id"]

    # Active subscription with 1 missing period
    sub1 = c.execute(
        """
        INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
        VALUES (%(cust_id)s, %(plan_id)s, '2026-01-01', '2026-06-30', %(pt_id)s, 'active')
        RETURNING id
        """,
        {"cust_id": cust_id, "plan_id": plan_id, "pt_id": pt_id},
    ).fetchone()
    sub1_id = sub1["id"]

    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (
            %(sub_id)s, %(prod_id)s, 1, 20000, %(tax_id)s, 1800, false
        )
        """,
        {"sub_id": sub1_id, "prod_id": prod_id, "tax_id": tax_id},
    )

    # Paused subscription
    sub2 = c.execute(
        """
        INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status, is_paused)
        VALUES (%(cust_id)s, %(plan_id)s, '2026-01-01', '2026-06-30', %(pt_id)s, 'active', true)
        RETURNING id
        """,
        {"cust_id": cust_id, "plan_id": plan_id, "pt_id": pt_id},
    ).fetchone()
    sub2_id = sub2["id"]

    c.execute(
        """
        INSERT INTO subscription_pauses (subscription_id, paused_on)
        VALUES (%(sub_id)s, '2026-01-01')
        """,
        {"sub_id": sub2_id},
    )

    return {
        "user_id": user_id,
        "cust_id": cust_id,
        "pt_id": pt_id,
        "tax_id": tax_id,
        "prod_id": prod_id,
        "plan_id": plan_id,
        "sub1_id": sub1_id,
        "sub2_id": sub2_id,
    }


def test_run_billing_live_and_dry_mode():
    as_of = date(2026, 1, 15)

    with conn() as c:
        setup = setup_candidate_subscriptions(c)

    # 1. Dry run
    dry_run_id = run_billing(as_of=as_of, mode="dry", actor_id=setup["user_id"])
    with conn() as c:
        dry_run = c.execute("SELECT * FROM billing_runs WHERE id = %(id)s", {"id": dry_run_id}).fetchone()
        assert dry_run["status"] == "completed"
        assert dry_run["mode"] == "dry"
        assert dry_run["considered"] == 2
        # Dry run should report would-be invoices created without actually leaving rows in invoices table
        assert dry_run["invoices_created"] == 1
        assert dry_run["amount_minor"] > 0

        # Verify no actual invoices were committed
        inv_count = c.execute("SELECT COUNT(*) as cnt FROM invoices").fetchone()["cnt"]
        assert inv_count == 0

    # 2. Live run
    live_run_id = run_billing(as_of=as_of, mode="live", actor_id=setup["user_id"])
    with conn() as c:
        live_run = c.execute("SELECT * FROM billing_runs WHERE id = %(id)s", {"id": live_run_id}).fetchone()
        assert live_run["status"] == "completed"
        assert live_run["mode"] == "live"
        assert live_run["considered"] == 2
        assert live_run["invoices_created"] == 1

        # Check items
        items = c.execute("SELECT * FROM billing_run_items WHERE run_id = %(id)s", {"id": live_run_id}).fetchall()
        assert len(items) == 2
        dispositions = {i["subscription_id"]: i["disposition"] for i in items}
        assert dispositions[setup["sub1_id"]] == "billed"
        assert dispositions[setup["sub2_id"]] == "skipped_paused"

        # Accounting rule (§13.3): considered == count(items) and sum(periods_billed) == invoices_created
        assert live_run["considered"] == len(items)
        assert sum(i["periods_billed"] for i in items) == live_run["invoices_created"]

        # Run AGAIN: up_to_date for sub1
        second_run_id = run_billing(as_of=as_of, mode="live", actor_id=1)
        second_run = c.execute("SELECT * FROM billing_runs WHERE id = %(id)s", {"id": second_run_id}).fetchone()
        assert second_run["invoices_created"] == 0
        second_items = c.execute("SELECT * FROM billing_run_items WHERE run_id = %(id)s", {"id": second_run_id}).fetchall()
        disps = {i["subscription_id"]: i["disposition"] for i in second_items}
        assert disps[setup["sub1_id"]] == "up_to_date"


def _items_by_sub(c, run_id):
    rows = c.execute(
        "SELECT * FROM billing_run_items WHERE run_id = %(id)s", {"id": run_id}
    ).fetchall()
    return {row["subscription_id"]: row for row in rows}


def test_three_runs_create_no_duplicates():
    as_of = date(2026, 3, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)

    ids = [
        run_billing(as_of=as_of, mode="live", actor_id=setup["user_id"])
        for _ in range(3)
    ]
    with conn() as c:
        counts = [
            c.execute(
                "SELECT invoices_created FROM billing_runs WHERE id = %(id)s",
                {"id": run_id},
            ).fetchone()["invoices_created"]
            for run_id in ids
        ]
        assert counts[0] == 3
        assert counts[1:] == [0, 0]
        total = c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"]
        assert total == 3
        assert (
            c.execute(
                "SELECT COUNT(*) AS n FROM invoices WHERE period_start = '2026-01-01'"
            ).fetchone()["n"]
            == 1
        )


def test_closed_subscription_is_billed_and_marked_complete():
    as_of = date(2026, 1, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)
        c.execute(
            """
            UPDATE subscriptions
               SET status = 'closed', closed_on = '2026-01-10'
             WHERE id = %(id)s
            """,
            {"id": setup["sub1_id"]},
        )

    run_id = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[setup["sub1_id"]],
    )
    with conn() as c:
        item = _items_by_sub(c, run_id)[setup["sub1_id"]]
        assert item["disposition"] == "billed"
        assert item["periods_billed"] == 1
        sub = c.execute(
            "SELECT billing_complete FROM subscriptions WHERE id = %(id)s",
            {"id": setup["sub1_id"]},
        ).fetchone()
        assert sub["billing_complete"] is True


def test_cancelled_invoice_is_reported_voided_not_rebilled():
    as_of = date(2026, 1, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)
        c.execute(
            """
            INSERT INTO invoices (
                subscription_id, customer_id, period_start, period_end,
                issue_date, due_date, status, subtotal_minor, discount_minor,
                tax_minor, total_minor, amount_paid_minor
            ) VALUES (
                %(sub_id)s, %(cust_id)s, '2026-01-01', '2026-01-31',
                '2026-01-01', '2026-01-31', 'cancelled', 20000, 0, 3600, 23600, 0
            )
            """,
            {"sub_id": setup["sub1_id"], "cust_id": setup["cust_id"]},
        )

    run_id = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[setup["sub1_id"]],
    )
    with conn() as c:
        item = _items_by_sub(c, run_id)[setup["sub1_id"]]
        assert item["disposition"] == "skipped_period_voided"
        assert item["periods_billed"] == 0
        assert c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"] == 1


def test_catch_up_bills_every_missing_period():
    as_of = date(2026, 4, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)

    run_id = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[setup["sub1_id"]],
    )
    with conn() as c:
        item = _items_by_sub(c, run_id)[setup["sub1_id"]]
        assert item["disposition"] == "billed"
        assert item["periods_billed"] == 4
        assert len(item["invoice_ids"]) == 4


def test_catch_up_is_capped_at_36_per_run():
    as_of = date(2026, 3, 1)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)
        daily_plan = c.execute(
            """
            INSERT INTO plans (name, billing_interval, interval_count, price_minor)
            VALUES ('Daily Plan', 'day', 1, 0)
            RETURNING id
            """
        ).fetchone()
        sub = c.execute(
            """
            INSERT INTO subscriptions (
                customer_id, plan_id, start_date, expiry_date, payment_term_id, status
            ) VALUES (
                %(cust_id)s, %(plan_id)s, '2026-01-01', '2026-06-30', %(pt_id)s, 'active'
            ) RETURNING id
            """,
            {
                "cust_id": setup["cust_id"],
                "plan_id": daily_plan["id"],
                "pt_id": setup["pt_id"],
            },
        ).fetchone()
        sub_id = sub["id"]
        c.execute(
            """
            INSERT INTO subscription_lines (
                subscription_id, product_id, quantity, unit_price_minor,
                tax_id, tax_rate_bps, tax_inclusive
            ) VALUES (
                %(sub_id)s, %(prod_id)s, 1, 20000, %(tax_id)s, 1800, false
            )
            """,
            {
                "sub_id": sub_id,
                "prod_id": setup["prod_id"],
                "tax_id": setup["tax_id"],
            },
        )

    first = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[sub_id],
    )
    second = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[sub_id],
    )
    third = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[sub_id],
    )
    with conn() as c:
        first_item = _items_by_sub(c, first)[sub_id]
        second_item = _items_by_sub(c, second)[sub_id]
        third_item = _items_by_sub(c, third)[sub_id]
        assert first_item["periods_billed"] == 36
        assert second_item["periods_billed"] == 24
        assert third_item["periods_billed"] == 0
        assert c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"] == 60


def test_subscription_ids_filter_and_auto_confirm():
    as_of = date(2026, 1, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)

    run_id = run_billing(
        as_of=as_of,
        mode="live",
        actor_id=setup["user_id"],
        subscription_ids=[setup["sub1_id"]],
        auto_confirm=True,
    )
    with conn() as c:
        run = c.execute(
            "SELECT * FROM billing_runs WHERE id = %(id)s", {"id": run_id}
        ).fetchone()
        assert run["considered"] == 1
        items = _items_by_sub(c, run_id)
        assert set(items) == {setup["sub1_id"]}
        inv = c.execute("SELECT * FROM invoices").fetchone()
        assert inv["status"] == "confirmed"
        assert inv["number"] is not None
        assert c.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"] >= 1


def test_dry_run_does_not_touch_discount_usage():
    as_of = date(2026, 1, 15)
    with conn() as c:
        setup = setup_candidate_subscriptions(c)
        discount = c.execute(
            """
            INSERT INTO discounts (
                name, kind, value, starts_on, ends_on, scope, usage_limit, auto_apply
            ) VALUES (
                'Run discount', 'percent', 1000, '2026-01-01', '2026-12-31',
                'subscription', 5, true
            ) RETURNING id
            """
        ).fetchone()

    run_billing(as_of=as_of, mode="dry", actor_id=setup["user_id"])
    with conn() as c:
        usage = c.execute(
            "SELECT usage_count FROM discounts WHERE id = %(id)s",
            {"id": discount["id"]},
        ).fetchone()["usage_count"]
        assert usage == 0
        assert c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"] == 0
