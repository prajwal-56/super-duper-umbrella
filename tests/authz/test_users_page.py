"""The staff users page: admin-only, role fixed to staff, every creation audited."""

from __future__ import annotations

STAFF_FORM = {"name": "Sam Staff", "email": "sam@example.com", "password": "GoodPass#123"}


def _admin_id(db) -> int:
    return int(db.execute("SELECT id FROM users WHERE email = 'admin@example.com'").fetchone()["id"])


def test_admin_creates_staff(as_role, client, db):
    as_role("admin")

    response = client.post("/app/users", data=STAFF_FORM, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/app/users?created=1"
    row = db.execute(
        "SELECT role, is_active, customer_id FROM users WHERE email = 'sam@example.com'"
    ).fetchone()
    assert row["role"] == "staff"
    assert row["is_active"] is True
    assert row["customer_id"] is None


def test_creation_is_audited_with_the_admin_as_actor(as_role, client, db):
    as_role("admin")
    admin_id = _admin_id(db)

    client.post("/app/users", data=STAFF_FORM, follow_redirects=False)

    entry = db.execute(
        "SELECT actor_id, action, entity, after FROM audit_log "
        "WHERE action = 'user.created' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert entry["actor_id"] == admin_id
    assert entry["entity"] == "users"
    assert entry["after"]["role"] == "staff"


def test_staff_cannot_reach_the_users_page(as_role, client, db):
    as_role("staff")

    assert client.get("/app/users").status_code == 403
    response = client.post("/app/users", data=STAFF_FORM, follow_redirects=False)
    assert response.status_code == 403
    assert db.execute(
        "SELECT 1 FROM users WHERE email = 'sam@example.com'"
    ).fetchone() is None


def test_customer_cannot_reach_the_users_page(as_role, client):
    as_role("customer")

    assert client.get("/app/users").status_code == 403


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get("/app/users", headers={"Accept": "text/html"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/app/users"


def test_users_page_lists_every_account(as_role, client, create_user):
    as_role("admin")
    create_user(role="staff", email="second@example.com")

    response = client.get("/app/users")

    assert response.status_code == 200
    assert "admin@example.com" in response.text
    assert "second@example.com" in response.text


def test_a_weak_password_returns_the_page_with_messages(as_role, client, db):
    as_role("admin")

    response = client.post(
        "/app/users",
        data={"name": "Sam Staff", "email": "sam@example.com", "password": "short"},
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert "more than 8 characters" in response.text
    assert db.execute(
        "SELECT 1 FROM users WHERE email = 'sam@example.com'"
    ).fetchone() is None


def test_a_duplicate_email_returns_422(as_role, client, create_user):
    as_role("admin")
    create_user(role="staff", email="sam@example.com")

    response = client.post("/app/users", data=STAFF_FORM, follow_redirects=False)

    assert response.status_code == 422
    assert "already exists" in response.text


def test_the_form_cannot_mint_an_admin(as_role, client, db):
    """The role is fixed server-side; a posted role field is ignored."""
    as_role("admin")

    client.post(
        "/app/users",
        data={**STAFF_FORM, "role": "admin"},
        follow_redirects=False,
    )

    row = db.execute("SELECT role FROM users WHERE email = 'sam@example.com'").fetchone()
    assert row["role"] == "staff"


def test_the_users_link_appears_only_for_admins(as_role, client):
    as_role("admin")
    assert "Users" in client.get("/").text

    as_role("staff", email="staff2@example.com")
    assert "Users" not in client.get("/").text
