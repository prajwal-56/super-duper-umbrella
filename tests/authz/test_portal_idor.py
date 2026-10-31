"""The customer portal: own data only, another customer's id is a 404."""

from __future__ import annotations

from app.db import conn


def _seed() -> dict:
    """Two customers, each with a plan, a subscription and a confirmed invoice."""
    rows: dict[str, dict] = {}
    with conn() as c:
        term = c.execute(
            "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
        ).fetchone()
        for index, (name, email) in enumerate(
            (("Asha Trading", "asha@example.com"), ("Other Customer", "other@example.com")),
            start=1,
        ):
            customer = c.execute(
                "INSERT INTO customers (name, email) VALUES (%s, %s) RETURNING id",
                (name, email),
            ).fetchone()
            plan = c.execute(
                "INSERT INTO plans (name, price_minor, billing_interval) "
                "VALUES (%s, 500000, 'month') RETURNING id",
                (f"{name} plan",),
            ).fetchone()
            sub = c.execute(
                "INSERT INTO subscriptions "
                "(customer_id, plan_id, payment_term_id, start_date, expiry_date) "
                "VALUES (%s, %s, %s, DATE '2026-10-01', DATE '2027-10-01') RETURNING id",
                (customer["id"], plan["id"], term["id"]),
            ).fetchone()
            invoice = c.execute(
                "INSERT INTO invoices "
                "(number, subscription_id, customer_id, period_start, period_end, "
                " issue_date, due_date, status, subtotal_minor, tax_minor, total_minor) "
                "VALUES (%s, %s, %s, DATE '2026-10-01', DATE '2026-10-31', "
                " DATE '2026-10-01', DATE '2026-10-31', 'confirmed', 500000, 90000, 590000) "
                "RETURNING id",
                (f"INV-2026-00000{index}", sub["id"], customer["id"]),
            ).fetchone()
            rows[name] = {
                "customer_id": int(customer["id"]),
                "subscription_id": int(sub["id"]),
                "invoice_id": int(invoice["id"]),
            }
    return rows


def _customer_client(email: str, create_user, password: str = "GoodPass#123"):
    """A signed-in client whose user is linked to the seeded customer row."""
    from fastapi.testclient import TestClient

    from app.main import app

    create_user(role="customer", email=email, password=password)
    with conn() as c:
        customer = c.execute(
            "SELECT id FROM customers WHERE email = %s ORDER BY id LIMIT 1", (email,)
        ).fetchone()
        c.execute(
            "UPDATE users SET customer_id = %s WHERE email = %s", (customer["id"], email)
        )
    client = TestClient(app, base_url="http://testserver")
    response = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert response.status_code == 303
    return client


def test_a_customer_sees_their_own_subscriptions(create_user):
    _seed()
    client = _customer_client("asha@example.com", create_user)

    body = client.get("/portal").text

    assert "Asha Trading" in body
    assert "SUB-" in body
    assert "Other Customer" not in body


def test_another_customers_subscription_is_a_404(create_user):
    rows = _seed()
    client = _customer_client("asha@example.com", create_user)

    response = client.get(f"/portal/subscriptions/{rows['Other Customer']['subscription_id']}")

    assert response.status_code == 404


def test_another_customers_invoice_is_a_404(create_user):
    rows = _seed()
    client = _customer_client("asha@example.com", create_user)

    response = client.get(f"/portal/invoices/{rows['Other Customer']['invoice_id']}")

    assert response.status_code == 404


def test_a_customer_can_open_their_own_invoice(create_user):
    rows = _seed()
    client = _customer_client("asha@example.com", create_user)

    response = client.get(f"/portal/invoices/{rows['Asha Trading']['invoice_id']}")

    assert response.status_code == 200
    assert "INV-2026-000001" in response.text
    assert "5,900.00" in response.text


def test_a_customer_sees_only_their_own_invoices(create_user):
    _seed()
    client = _customer_client("asha@example.com", create_user)

    body = client.get("/portal/invoices").text

    assert "INV-2026-000001" in body
    assert "INV-2026-000002" not in body


def test_staff_cannot_open_the_customer_portal(as_role, client):
    as_role("staff")

    assert client.get("/portal").status_code == 403
