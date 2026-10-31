from datetime import date
from types import SimpleNamespace

from app import clock
from app.db import conn
from app.jobs import daily


def _confirmed_subscription(c):
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Daily Co', 'daily@example.com') RETURNING id"
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
        VALUES ('Daily Seat', 'service', 20000, %(tax)s) RETURNING id
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
            %(cust)s, %(plan)s, '2026-01-01', '2026-06-30', %(pt)s, 'confirmed'
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
        ) VALUES (%(sub)s, %(prod)s, 1, 20000, %(tax)s, 1800, false)
        """,
        {"sub": sub_id, "prod": product["id"], "tax": tax["id"]},
    )
    return sub_id


def test_daily_job_activates_and_bills_once():
    clock.set_simulated(date(2026, 1, 15), None)
    with conn() as c:
        sub_id = _confirmed_subscription(c)

    result = daily.run()

    assert result["as_of"] == "2026-01-15"
    assert result["activated"] == 1
    assert result["closed"] == 0
    assert isinstance(result["billing_run_id"], int)

    with conn() as c:
        sub = c.execute(
            "SELECT status FROM subscriptions WHERE id = %(id)s", {"id": sub_id}
        ).fetchone()
        assert sub["status"] == "active"
        invoices = c.execute(
            "SELECT COUNT(*) AS n FROM invoices WHERE subscription_id = %(id)s",
            {"id": sub_id},
        ).fetchone()["n"]
        assert invoices == 1
        run = c.execute(
            "SELECT * FROM billing_runs WHERE id = %(id)s",
            {"id": result["billing_run_id"]},
        ).fetchone()
        assert run["status"] == "completed"
        assert run["mode"] == "live"
        assert run["considered"] == 1


def test_internal_daily_requires_cron_token(client, monkeypatch):
    from app.routes import internal

    monkeypatch.setattr(
        internal, "settings", SimpleNamespace(cron_token="super-secret-token")
    )

    missing = client.post("/internal/daily")
    assert missing.status_code == 403

    wrong = client.post(
        "/internal/daily", headers={"X-Cron-Token": "not-it"}
    )
    assert wrong.status_code == 403

    ok = client.post(
        "/internal/daily", headers={"X-Cron-Token": "super-secret-token"}
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["activated"] == 0
    assert body["closed"] == 0
    assert isinstance(body["billing_run_id"], int)

    with conn() as c:
        run = c.execute(
            "SELECT status FROM billing_runs WHERE id = %(id)s",
            {"id": body["billing_run_id"]},
        ).fetchone()
        assert run["status"] == "completed"


def test_internal_daily_is_closed_when_token_is_unset(client, monkeypatch):
    from app.routes import internal

    monkeypatch.setattr(internal, "settings", SimpleNamespace(cron_token=""))

    response = client.post("/internal/daily", headers={"X-Cron-Token": ""})
    assert response.status_code == 403
