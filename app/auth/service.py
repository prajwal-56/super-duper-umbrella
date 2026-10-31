"""Account, login and password-reset operations. One transaction per operation."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import psycopg

from app.audit import audit
from app.auth.passwords import hash_password, validate_password, verify_password
from app.config import settings
from app.deps import User
from app.outbox import queue_email

RESET_TOKEN_MINUTES = 30


class InvalidPassword(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class EmailTaken(ValueError):
    pass


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_account(
    conn: psycopg.Connection,
    name: str,
    email: str,
    password: str,
    role: str = "customer",
    actor_id: int | None = None,
) -> int:
    """Create a customer (and its customer record) or a staff/admin user.

    Raises InvalidPassword for rule violations and EmailTaken for a duplicate
    address (case-insensitive, enforced by the CITEXT unique constraint).
    Returns the new user id.
    """
    errors = validate_password(password)
    if errors:
        raise InvalidPassword(errors)
    email = normalize_email(email)
    name = (name or "").strip()
    if not name:
        raise ValueError("Name is required")
    if not email or "@" not in email:
        raise ValueError("A valid email address is required")

    existing = conn.execute("SELECT 1 FROM users WHERE email = %s", (email,)).fetchone()
    if existing:
        raise EmailTaken(email)

    customer_id: int | None = None
    if role == "customer":
        row = conn.execute(
            "INSERT INTO customers (name, email) VALUES (%s, %s) RETURNING id",
            (name, email),
        ).fetchone()
        customer_id = int(row["id"])

    try:
        row = conn.execute(
            """
            INSERT INTO users (email, password_hash, role, customer_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (email, hash_password(password), role, customer_id),
        ).fetchone()
    except psycopg.errors.UniqueViolation as exc:
        raise EmailTaken(email) from exc

    user_id = int(row["id"])
    audit(
        conn,
        actor_id if actor_id is not None else user_id,
        "user.created",
        "users",
        user_id,
        after={"email": email, "role": role, "customer_id": customer_id},
    )
    return user_id


def authenticate(email: str, password: str) -> User | None:
    """Return the active User for valid credentials, else None."""
    row = conn_fetch_user(normalize_email(email))
    if row is None or not row["is_active"]:
        return None
    if not verify_password(row["password_hash"], password or ""):
        return None
    return User(
        id=int(row["id"]),
        email=str(row["email"]),
        role=str(row["role"]),
        customer_id=row["customer_id"],
    )


def conn_fetch_user(email: str) -> dict | None:
    from app.db import fetch_one

    return fetch_one(
        "SELECT id, email, password_hash, role, customer_id, is_active "
        "FROM users WHERE email = %s",
        (email,),
    )


def create_reset_request(conn: psycopg.Connection, email: str) -> str | None:
    """Create a single-use reset token and queue the email.

    Returns the raw token for tests; the route never exposes it. Returns None
    when the address is unknown (the caller shows the same response either way).
    """
    row = conn.execute(
        "SELECT id, email FROM users WHERE email = %s AND is_active", (normalize_email(email),)
    ).fetchone()
    if row is None:
        return None

    now = datetime.now(UTC)  # real-time-ok: reset token expiry is wall-clock security state
    token = secrets.token_urlsafe(32)
    conn.execute(
        "UPDATE password_reset_tokens SET used_at = %s WHERE user_id = %s AND used_at IS NULL",
        (now, row["id"]),
    )
    conn.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s)
        """,
        (row["id"], _hash_token(token), now + timedelta(minutes=RESET_TOKEN_MINUTES)),
    )
    link = f"{settings.app_base_url}/reset/{token}"
    queue_email(
        conn,
        kind="password_reset",
        to_email=str(row["email"]),
        subject="Reset your Brightloop password",
        body_html=(
            "<p>A password reset was requested for your Brightloop Ledger account.</p>"
            f'<p><a href="{link}">Reset your password</a></p>'
            f"<p>This link expires in {RESET_TOKEN_MINUTES} minutes and can be used once.</p>"
            "<p>If you did not ask for this, you can ignore the message.</p>"
        ),
        link=link,
    )
    audit(
        conn,
        int(row["id"]),
        "user.password_reset_requested",
        "users",
        int(row["id"]),
        after={"expires_in_minutes": RESET_TOKEN_MINUTES},
    )
    return token


def find_reset_token(conn: psycopg.Connection, token: str) -> dict | None:
    """Return the token row when it is unused and unexpired, else None."""
    row = conn.execute(
        """
        SELECT id, user_id, expires_at, used_at
        FROM password_reset_tokens WHERE token_hash = %s
        """,
        (_hash_token(token),),
    ).fetchone()
    if row is None or row["used_at"] is not None:
        return None
    now = datetime.now(UTC)  # real-time-ok: reset token expiry is wall-clock security state
    if row["expires_at"] <= now:
        return None
    return row


def consume_reset(conn: psycopg.Connection, token: str, new_password: str) -> int | None:
    """Set a new password for a valid token. Returns the user id or None."""
    errors = validate_password(new_password)
    if errors:
        raise InvalidPassword(errors)
    row = find_reset_token(conn, token)
    if row is None:
        return None
    user_id = int(row["user_id"])
    conn.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_password(new_password), user_id),
    )
    conn.execute(
        "UPDATE password_reset_tokens SET used_at = %s WHERE id = %s",
        (datetime.now(UTC), row["id"]),  # real-time-ok: token bookkeeping
    )
    audit(conn, user_id, "user.password_reset", "users", user_id)
    return user_id


def ensure_admin() -> bool:
    """Create the first admin from ADMIN_EMAIL/ADMIN_PASSWORD when none exists."""
    if not settings.admin_password:
        return False
    from app.db import conn

    with conn() as c:
        existing = c.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        if existing:
            return False
        create_account(
            c,
            name="Brightloop Admin",
            email=settings.admin_email,
            password=settings.admin_password,
            role="admin",
            actor_id=None,
        )
    return True
