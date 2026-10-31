"""Migration runner: applies every unapplied db/migrations/*.sql in filename order.

Usage:
    python -m app.migrate                 # apply to DATABASE_URL
    python -m app.migrate --test          # apply to TEST_DATABASE_URL
    python -m app.migrate --reset --test  # drop the schema first (tests only)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"

CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _admin_conninfo(conninfo: str) -> str:
    params = conninfo_to_dict(conninfo)
    params["dbname"] = "postgres"
    return make_conninfo(**params)


def ensure_database(conninfo: str) -> bool:
    """Create the database if it does not exist. Returns True when created."""
    params = conninfo_to_dict(conninfo)
    dbname = params.get("dbname")
    if not dbname:
        raise ValueError("connection string has no database name")
    with psycopg.connect(_admin_conninfo(conninfo), autocommit=True) as admin:
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if exists:
            return False
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        return True


def apply_all(conninfo: str, reset: bool = False) -> list[str]:
    """Apply unapplied migrations. Returns the filenames applied in this call."""
    ensure_database(conninfo)
    applied: list[str] = []
    with psycopg.connect(conninfo, autocommit=True) as c:
        if reset:
            c.execute("DROP SCHEMA public CASCADE")
            c.execute("CREATE SCHEMA public")
        c.execute(CREATE_MIGRATIONS_TABLE)
        done = {row[0] for row in c.execute("SELECT filename FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            statement = path.read_text()
            with c.transaction():
                c.execute(statement)
                c.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                )
            applied.append(path.name)
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--test", action="store_true", help="use TEST_DATABASE_URL")
    parser.add_argument("--reset", action="store_true", help="drop the schema first")
    args = parser.parse_args(argv)

    conninfo = settings.test_database_url if args.test else settings.database_url
    applied = apply_all(conninfo, reset=args.reset)
    for name in applied:
        print(f"applied {name}")
    print(f"migrate: {len(applied)} applied, database ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
