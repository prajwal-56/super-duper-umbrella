"""Base schema: tables, the idempotency index and the audit trigger."""

import psycopg
import pytest


def test_expected_tables_exist(db):
    rows = db.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall()
    tables = {row["tablename"] for row in rows}
    expected = {
        "customers",
        "users",
        "password_reset_tokens",
        "taxes",
        "payment_terms",
        "products",
        "product_variants",
        "plans",
        "product_plan_prices",
        "quotation_templates",
        "quotation_template_lines",
        "subscriptions",
        "subscription_lines",
        "subscription_pauses",
        "discounts",
        "subscription_discounts",
        "billing_runs",
        "invoices",
        "invoice_lines",
        "discount_redemptions",
        "payments",
        "billing_run_items",
        "audit_log",
        "emails_outbox",
        "clock_state",
        "schema_migrations",
    }
    assert expected <= tables


def test_unique_invoice_period_is_partial(db):
    row = db.execute(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_invoice_period'"
    ).fetchone()
    assert row is not None
    assert "UNIQUE" in row["indexdef"]
    assert "cancelled" in row["indexdef"]


def test_audit_log_is_append_only():
    from app.db import conn

    with conn() as c:
        c.execute(
            "INSERT INTO audit_log (actor_id, action, entity, entity_id) "
            "VALUES (NULL, 'test', 'test', 1)"
        )
    with pytest.raises(psycopg.errors.RaiseException):
        with conn() as c:
            c.execute("UPDATE audit_log SET action = 'changed' WHERE entity = 'test'")
    with pytest.raises(psycopg.errors.RaiseException):
        with conn() as c:
            c.execute("DELETE FROM audit_log WHERE entity = 'test'")


def test_clock_state_has_one_row(db):
    rows = db.execute("SELECT id, mode FROM clock_state").fetchall()
    assert len(rows) == 1
    assert rows[0]["mode"] == "real"
