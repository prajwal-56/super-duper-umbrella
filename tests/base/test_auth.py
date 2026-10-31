"""Signup, login, logout, forgot and reset (R-AUTH-01..04)."""

import re

from app.auth.passwords import validate_password
from app.db import conn


def _outbox_rows():
    with conn() as c:
        return c.execute(
            "SELECT kind, to_email, subject, link FROM emails_outbox ORDER BY id"
        ).fetchall()


def _token_from_link(link: str) -> str:
    match = re.search(r"/reset/([^/]+)$", link)
    assert match, link
    return match.group(1)


def test_password_rule_boundaries():
    assert validate_password("Aa1!aaaa")  # exactly 8 characters -> too short
    assert validate_password("Aa1!aaaaa") == []  # 9 characters, all classes
    assert validate_password("aa1!aaaaa")  # no uppercase
    assert validate_password("AA1!AAAAA")  # no lowercase
    assert validate_password("Aa1aaaaaa")  # no special character


def test_signup_rejects_exactly_eight_characters(client):
    response = client.post(
        "/signup",
        data={"name": "Eight", "email": "eight@example.com", "password": "Aa1!aaaa"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "more than 8 characters" in response.text.lower()
    with conn() as c:
        assert c.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0


def test_signup_creates_customer_and_ignores_role(client):
    response = client.post(
        "/signup",
        data={
            "name": "Asha Rao",
            "email": "Asha@Example.com",
            "password": "GoodPass#123",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?signed_up=1"
    with conn() as c:
        user = c.execute("SELECT email, role, customer_id FROM users").fetchone()
        assert user["role"] == "customer"
        assert str(user["email"]) == "asha@example.com"
        assert user["customer_id"] is not None
        customer = c.execute("SELECT name, email FROM customers").fetchone()
        assert customer["name"] == "Asha Rao"


def test_duplicate_email_is_case_insensitive(client):
    data = {"name": "One", "email": "dup@example.com", "password": "GoodPass#123"}
    assert client.post("/signup", data=data, follow_redirects=False).status_code == 303
    response = client.post(
        "/signup",
        data={**data, "email": "DUP@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 422
    assert "already exists" in response.text.lower()
    with conn() as c:
        assert c.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1


def test_login_and_logout(client, create_user):
    create_user(email="staff@example.com", role="staff")
    bad = client.post(
        "/login",
        data={"email": "staff@example.com", "password": "WrongPass#1"},
        follow_redirects=False,
    )
    assert bad.status_code == 401

    good = client.post(
        "/login",
        data={"email": "STAFF@example.com", "password": "GoodPass#123"},
        follow_redirects=False,
    )
    assert good.status_code == 303
    assert "brightloop_session" in good.cookies
    page = client.get("/")
    assert page.status_code == 200
    assert "staff@example.com" in page.text

    out = client.post("/logout", follow_redirects=False)
    assert out.status_code == 303
    assert client.get("/", follow_redirects=False).status_code == 303


def test_login_rejects_cross_origin_post(client):
    response = client.post(
        "/login",
        data={"email": "x@example.com", "password": "GoodPass#123"},
        headers={"Origin": "http://evil.example"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_forgot_is_identical_for_known_and_unknown(client, create_user):
    create_user(email="known@example.com")
    known = client.post("/forgot", data={"email": "known@example.com"})
    unknown = client.post("/forgot", data={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert "If that email address is registered" in known.text
    assert "If that email address is registered" in unknown.text
    rows = _outbox_rows()
    assert len(rows) == 1
    assert rows[0]["to_email"] == "known@example.com"


def test_reset_token_is_single_use(client, create_user):
    create_user(email="reset@example.com")
    client.post("/forgot", data={"email": "reset@example.com"})
    link = _outbox_rows()[0]["link"]
    token = _token_from_link(link)

    page = client.get(f"/reset/{token}")
    assert page.status_code == 200

    weak = client.post(
        f"/reset/{token}",
        data={"password": "Aa1!aaaa", "password_confirm": "Aa1!aaaa"},
        follow_redirects=False,
    )
    assert weak.status_code == 422

    ok = client.post(
        f"/reset/{token}",
        data={"password": "NewPass#456", "password_confirm": "NewPass#456"},
        follow_redirects=False,
    )
    assert ok.status_code == 303

    login = client.post(
        "/login",
        data={"email": "reset@example.com", "password": "NewPass#456"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    reuse = client.get(f"/reset/{token}")
    assert reuse.status_code == 410
