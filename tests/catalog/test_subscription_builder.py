"""Tests for subscription builder service: create_draft, create_from_template."""

from __future__ import annotations

import pytest

from app.clock import today
from app.services import catalog as cat_svc
from app.services.subscription_builder import create_draft, create_from_template


@pytest.fixture
def plan_basic(db):
    return cat_svc.create_plan(
        db,
        name="Basic Monthly",
        price_minor=0,
        billing_interval="month",
        interval_count=1,
        min_quantity=1,
        available_from=None,
        available_to=None,
        auto_close=False,
        allow_early_close=True,
        allow_pause=True,
        allow_renew=True,
        actor_id=1,
    )


@pytest.fixture
def term_immediate(db):
    return cat_svc.create_payment_term(db, "Immediate", 0, actor_id=1)


@pytest.fixture
def product_standard(db):
    return cat_svc.create_product(
        db, "Service A", "service", 10000, 5000, None, None, actor_id=1
    )


@pytest.fixture
def customer_sample(db):
    row = db.execute(
        "INSERT INTO customers (name, email) VALUES ('Test Customer', 'cust@example.com') RETURNING id"
    ).fetchone()
    return int(row["id"])


def test_create_draft_success(db, customer_sample, plan_basic, term_immediate, product_standard):
    sub_id = create_draft(
        db,
        customer_id=customer_sample,
        plan_id=plan_basic,
        start_date=today(),
        expiry_date=today(),
        payment_term_id=term_immediate,
        lines=[{"product_id": product_standard, "quantity": 2}],
    )
    assert sub_id > 0
    row = db.execute("SELECT status, number FROM subscriptions WHERE id = %s", (sub_id,)).fetchone()
    assert row["status"] == "draft"
    assert row["number"].startswith("SUB-")

    line = db.execute("SELECT * FROM subscription_lines WHERE subscription_id = %s", (sub_id,)).fetchone()
    assert line["quantity"] == 2
    assert line["unit_price_minor"] == 10000


def test_create_from_template(db, customer_sample, plan_basic, term_immediate, product_standard):
    tmpl_row = db.execute(
        """
        INSERT INTO quotation_templates (name, plan_id, validity_days, payment_term_id)
        VALUES ('Template A', %s, 30, %s)
        RETURNING id
        """,
        (plan_basic, term_immediate),
    ).fetchone()
    tmpl_id = int(tmpl_row["id"])

    db.execute(
        """
        INSERT INTO quotation_template_lines (template_id, product_id, quantity)
        VALUES (%s, %s, 1)
        """,
        (tmpl_id, product_standard),
    )

    sub_id = create_from_template(
        db,
        template_id=tmpl_id,
        customer_id=customer_sample,
        start_date=today(),
        actor_id=None,
    )
    assert sub_id > 0
    row = db.execute("SELECT status, template_id FROM subscriptions WHERE id = %s", (sub_id,)).fetchone()
    assert row["status"] == "draft"
    assert row["template_id"] == tmpl_id
