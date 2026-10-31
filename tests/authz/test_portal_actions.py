"""Portal actions: only what allowed_actions returns, only on your own subscription."""

from __future__ import annotations

from app.db import conn


def _seed_active() -> dict:
    """Two customers, each with an active subscription on a pausable plan."""
    rows: dict[str, dict] = {}
    with conn() as c:
        term = c.execute(
            "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
        ).fetchone()
        for name, email in (("Asha Trading", "asha@example.com"), ("Other Co", "other@example.com")):
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
                "(customer_id, plan_id, payment_term_id, status, start_date, expiry_date) "
                "VALUES (%s, %s, %s, 'active', DATE '2026-10-01', DATE '2027-10-01') RETURNING id",
                (customer["id"], plan["id"], term["id"]),
            ).fetchone()
            rows[name] = {
                "customer_id": int(customer["id"]),
                "subscription_id": int(sub["id"]),
            }
    return rows


def _client(email: str, create_user, password: str = "GoodPass#123"):
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


def _is_paused(subscription_id: int) -> bool:
    with conn() as c:
        row = c.execute(
            "SELECT is_paused FROM subscriptions WHERE id = %s", (subscription_id,)
        ).fetchone()
    return bool(row["is_paused"])


def test_a_customer_pauses_their_own_subscription(create_user):
    rows = _seed_active()
    client = _client("asha@example.com", create_user)
    sub_id = rows["Asha Trading"]["subscription_id"]

    response = client.post(
        f"/portal/subscriptions/{sub_id}/action",
        data={"action": "pause"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert _is_paused(sub_id) is True


def test_the_detail_page_offers_only_the_allowed_actions(create_user):
    rows = _seed_active()
    client = _client("asha@example.com", create_user)
    sub_id = rows["Asha Trading"]["subscription_id"]

    body = client.get(f"/portal/subscriptions/{sub_id}").text

    assert "Pause" in body
    assert "Activate" not in body


def test_an_action_that_is_not_allowed_is_a_409(create_user):
    rows = _seed_active()
    client = _client("asha@example.com", create_user)
    sub_id = rows["Asha Trading"]["subscription_id"]

    response = client.post(
        f"/portal/subscriptions/{sub_id}/action",
        data={"action": "confirm"},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "not available" in response.text


def test_a_customer_cannot_act_on_another_customers_subscription(create_user):
    rows = _seed_active()
    client = _client("asha@example.com", create_user)
    other = rows["Other Co"]["subscription_id"]

    response = client.post(
        f"/portal/subscriptions/{other}/action",
        data={"action": "pause"},
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert _is_paused(other) is False


def test_closing_records_the_reason(create_user):
    rows = _seed_active()
    client = _client("asha@example.com", create_user)
    sub_id = rows["Asha Trading"]["subscription_id"]

    response = client.post(
        f"/portal/subscriptions/{sub_id}/action",
        data={"action": "close", "reason": "moving to another provider"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    with conn() as c:
        row = c.execute(
            "SELECT status, close_reason FROM subscriptions WHERE id = %s", (sub_id,)
        ).fetchone()
    assert row["status"] == "closed"
    assert row["close_reason"] == "moving to another provider"
