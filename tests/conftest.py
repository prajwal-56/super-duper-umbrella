"""Pytest fixtures. Tests run against a real Postgres test database (BUILD_PLAN §19)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# These must be set before any app module is imported (app.config reads them once).
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/brightloop_test"
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["DEMO_MODE"] = "false"
os.environ["SEED_ON_BOOT"] = "false"
os.environ["DEV_AUTH_BYPASS"] = "0"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["APP_BASE_URL"] = "http://testserver"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "Admin#12345"

import pytest  # noqa: E402
from psycopg import sql  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    from app.config import settings
    from app.migrate import apply_all

    apply_all(settings.database_url, reset=True)
    yield
    from app.db import close_pool

    close_pool()


@pytest.fixture(autouse=True)
def clean_database(migrated_database):
    from app.db import conn

    with conn() as c:
        rows = c.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND tablename <> 'schema_migrations'"
        ).fetchall()
        names = [row["tablename"] for row in rows]
        if names:
            statement = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier(name) for name in names)
            )
            c.execute(statement)
        c.execute("INSERT INTO clock_state (id) VALUES (1)")
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def create_user():
    from app.auth.service import create_account
    from app.db import conn

    def _create(
        role: str = "customer",
        email: str | None = None,
        password: str = "GoodPass#123",
        name: str | None = None,
    ) -> int:
        email = email or f"{role}@example.com"
        name = name or f"Test {role.title()}"
        with conn() as c:
            return create_account(c, name=name, email=email, password=password, role=role)

    return _create


@pytest.fixture
def login(client):
    def _login(email: str, password: str = "GoodPass#123"):
        response = client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text
        return response

    return _login


@pytest.fixture
def as_role(client, create_user, login):
    def _as(role: str, email: str | None = None, password: str = "GoodPass#123"):
        email = email or f"{role}@example.com"
        create_user(role=role, email=email, password=password)
        login(email, password)
        return email

    return _as


@pytest.fixture
def db():
    from app.db import conn

    with conn() as c:
        yield c
