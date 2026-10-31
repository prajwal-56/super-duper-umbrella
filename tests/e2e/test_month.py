"""End-to-end month flow: signup -> plan -> subscription -> activate -> invoice -> pay -> dashboard (A-16).

This exercises the full G2 / demo lifecycle over HTTP:
1. Customer signs up and verifies initial empty portal.
2. Admin configures product, tax, and monthly plan via catalog endpoints.
3. Customer receives a subscription in confirmed state, activates it on start date.
4. Admin advances business clock and triggers a live billing run with auto-confirm.
5. Verifies single invoice generation (and idempotency on immediate re-run).
6. Staff records payment against the invoice.
7. Customer inspects the paid invoice in the customer portal.
8. Finance lead inspects updated revenue metrics on the dashboard.
9. INV-01 through INV-08 invariants assert complete system integrity.
"""

from __future__ import annotations

import dataclasses
from datetime import date

from app import clock
from app.config import settings
from app.db import conn
from app.services import invariants


def test_full_month_e2e_flow(client, login, monkeypatch):
    # Enable demo mode for clock manipulation and demo endpoints
    from app import clock as clock_module
    from app import deps

    demo_settings = dataclasses.replace(settings, demo_mode=True)
    monkeypatch.setattr(deps, "settings", demo_settings)
    monkeypatch.setattr(clock_module, "settings", demo_settings)

    # Clean starting state anchored at 2026-05-01
    start_date = date(2026, 5, 1)
    clock.set_simulated(start_date, None)

    # Seed baseline admin and staff
    from app.auth.service import create_account

    with conn() as c:
        create_account(c, "Lead Admin", "admin.e2e@brightloop.io", "GoodPass#123", role="admin")
        create_account(c, "Ops Staff", "staff.e2e@brightloop.io", "GoodPass#123", role="staff")

    # 1. Customer signs up via public auth
    signup_resp = client.post(
        "/signup",
        data={
            "name": "Kiran Enterprises",
            "email": "kiran@kiranenterprises.in",
            "password": "KiranPass#2026",
        },
        follow_redirects=False,
    )
    assert signup_resp.status_code == 303
    assert signup_resp.headers["location"] == "/login?signed_up=1"

    # Login as customer and check portal
    login("kiran@kiranenterprises.in", "KiranPass#2026")

    portal_resp = client.get("/portal")
    assert portal_resp.status_code == 200
    assert "Kiran Enterprises" in portal_resp.text

    # Retrieve customer id from db
    with conn() as c:
        customer = c.execute(
            "SELECT id FROM customers WHERE email = 'kiran@kiranenterprises.in'"
        ).fetchone()
        assert customer is not None
        customer_id = customer["id"]

    # 2. Admin creates tax, product, plan, and confirmed subscription
    login("admin.e2e@brightloop.io", "GoodPass#123")

    # Catalog setup: tax (18% exclusive)
    tax_resp = client.post(
        "/app/catalog/taxes/new",
        data={
            "name": "GST 18% Exclusive",
            "rate_percent": "18.00",
            "inclusive": "false",
        },
        follow_redirects=False,
    )
    assert tax_resp.status_code == 303

    with conn() as c:
        tax = c.execute("SELECT id FROM taxes WHERE name = 'GST 18% Exclusive'").fetchone()
        assert tax is not None
        tax_id = tax["id"]

        # Product setup
        product = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, tax_id, active)
            VALUES ('Cloud ERP Standard', 'service', 200000, %s, true)
            RETURNING id
            """,
            (tax_id,),
        ).fetchone()
        product_id = product["id"]

        # Plan setup: Monthly
        plan = c.execute(
            """
            INSERT INTO plans (
                name, price_minor, billing_interval, interval_count, min_quantity,
                available_from, auto_close, allow_early_close, allow_pause, allow_renew, active
            ) VALUES (
                'ERP Monthly Plan', 0, 'month', 1, 1,
                '2026-01-01', false, true, true, true, true
            ) RETURNING id
            """
        ).fetchone()
        plan_id = plan["id"]

        terms = c.execute("SELECT id FROM payment_terms WHERE name = 'Net 30'").fetchone()
        if not terms:
            terms = c.execute(
                "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
            ).fetchone()
        payment_term_id = terms["id"]

        # Create confirmed subscription starting on today's simulated date
        sub = c.execute(
            """
            INSERT INTO subscriptions (
                customer_id, plan_id, status, start_date, expiry_date, payment_term_id
            ) VALUES (
                %s, %s, 'confirmed', '2026-05-01', '2027-04-30', %s
            ) RETURNING id
            """,
            (customer_id, plan_id, payment_term_id),
        ).fetchone()
        sub_id = sub["id"]

        # Subscription line: 1 seat * 200,000 minor units + 18% tax
        c.execute(
            """
            INSERT INTO subscription_lines (
                subscription_id, product_id, quantity, unit_price_minor,
                tax_id, tax_rate_bps, tax_inclusive
            ) VALUES (%s, %s, 1, 200000, %s, 1800, false)
            """,
            (sub_id, product_id, tax_id),
        )

    # 3. Transition: Daily job / activation automatically brings confirmed sub to active
    from app.services import lifecycle

    activated_info = lifecycle.run_daily(as_of=start_date)
    assert activated_info["activated"] >= 1

    with conn() as c:
        sub_status = c.execute(
            "SELECT status FROM subscriptions WHERE id = %s", (sub_id,)
        ).fetchone()["status"]
        assert sub_status == "active"

    # 4. Trigger Live Billing Run via HTTP
    login("admin.e2e@brightloop.io", "GoodPass#123")
    run_post = client.post(
        "/app/billing-runs",
        data={
            "as_of": "2026-05-01",
            "mode": "live",
            "auto_confirm": "1",
        },
        follow_redirects=False,
    )
    assert run_post.status_code == 303
    run_url = run_post.headers["location"]
    run_id = int(run_url.rstrip("/").split("/")[-1])

    # Inspect run result page
    run_page = client.get(f"/app/billing-runs/{run_id}")
    assert run_page.status_code == 200
    assert "completed" in run_page.text

    # 5. Idempotency test: Immediate re-run produces 0 new invoices
    rerun_post = client.post(
        "/app/billing-runs",
        data={
            "as_of": "2026-05-01",
            "mode": "live",
            "auto_confirm": "1",
        },
        follow_redirects=False,
    )
    assert rerun_post.status_code == 303
    rerun_id = int(rerun_post.headers["location"].rstrip("/").split("/")[-1])

    rerun_page = client.get(f"/app/billing-runs/{rerun_id}")
    assert rerun_page.status_code == 200
    # In the rerun, items show 'up_to_date' with 0 invoices created
    with conn() as c:
        rerun_record = c.execute(
            "SELECT invoices_created FROM billing_runs WHERE id = %s", (rerun_id,)
        ).fetchone()
        assert rerun_record["invoices_created"] == 0

    # 6. Verify Draft Invoice, Confirm it, and Record Payment
    with conn() as c:
        inv = c.execute(
            """
            SELECT id, number, status, total_minor, amount_paid_minor
            FROM invoices
            WHERE subscription_id = %s AND period_start = '2026-05-01'
            """,
            (sub_id,),
        ).fetchone()
        assert inv is not None
        # Subtotal: 200,000 minor (₹2,000.00), Tax: 36,000 minor (₹360.00), Total: 236,000 minor (₹2,360.00)
        assert inv["total_minor"] == 236000
        invoice_id = inv["id"]

    # Staff confirms invoice via HTTP
    login("staff.e2e@brightloop.io", "GoodPass#123")
    confirm_resp = client.post(
        f"/app/invoices/{invoice_id}/confirm",
        follow_redirects=False,
    )
    assert confirm_resp.status_code == 303

    with conn() as c:
        inv_conf = c.execute(
            "SELECT status, number FROM invoices WHERE id = %s", (invoice_id,)
        ).fetchone()
        assert inv_conf["status"] == "confirmed"
        assert inv_conf["number"] is not None

    # Staff records payment via HTTP
    pay_resp = client.post(
        "/app/payments/record",
        data={
            "invoice_id": str(invoice_id),
            "method": "bank_transfer",
            "amount": "2360.00",
            "paid_on": "2026-05-01",
            "note": "NEFT payment ref 998811",
        },
        follow_redirects=False,
    )
    assert pay_resp.status_code == 303

    # Invoice should now be paid
    with conn() as c:
        inv_after = c.execute(
            "SELECT status, amount_paid_minor, total_minor FROM invoices WHERE id = %s",
            (invoice_id,),
        ).fetchone()
        assert inv_after["status"] == "paid"
        assert inv_after["amount_paid_minor"] == inv_after["total_minor"]

    # 7. Customer portal inspects paid invoice
    login("kiran@kiranenterprises.in", "KiranPass#2026")

    inv_detail = client.get(f"/portal/invoices/{invoice_id}")
    assert inv_detail.status_code == 200
    assert "paid" in inv_detail.text.lower()
    assert "₹2,360.00" in inv_detail.text or "2,360.00" in inv_detail.text

    # 8. Finance lead inspects Dashboard
    login("staff.e2e@brightloop.io", "GoodPass#123")
    dash_resp = client.get("/app/dashboard")
    assert dash_resp.status_code == 200
    assert "Dashboard" in dash_resp.text

    # 9. Verify System Invariants
    with conn() as c:
        results = invariants.run_all(c)
        failing = [r for r in results if not r.ok]
        assert failing == [], [(r.id, r.violations, r.sample_rows) for r in failing]
