from datetime import date

import pytest
from fastapi import HTTPException

from app.db import conn
from app.services.lifecycle import (
    allowed_actions,
    close,
    pause,
    renew,
    resume,
    run_daily,
    transition,
)


def create_customer_plan_term(c):
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Acme Corp', 'acme@example.com') RETURNING id"
    ).fetchone()
    cust_id = cust["id"]

    pt = c.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
    ).fetchone()
    pt_id = pt["id"]

    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, auto_close, allow_early_close, allow_pause, allow_renew)
        VALUES ('Standard Monthly', 'month', 1, false, true, true, true)
        RETURNING id
        """
    ).fetchone()
    plan_id = plan["id"]

    strict_plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, auto_close, allow_early_close, allow_pause, allow_renew)
        VALUES ('Strict Annual', 'year', 1, true, false, false, false)
        RETURNING id
        """
    ).fetchone()
    strict_plan_id = strict_plan["id"]

    return {
        "cust_id": cust_id,
        "pt_id": pt_id,
        "plan_id": plan_id,
        "strict_plan_id": strict_plan_id,
    }


def test_subscription_lifecycle_transitions():
    start = date(2026, 1, 1)
    expiry = date(2026, 12, 31)

    with conn() as c:
        setup = create_customer_plan_term(c)
        sub = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(plan_id)s, %(start)s, %(expiry)s, %(pt_id)s, 'draft')
            RETURNING id, version
            """,
            {**setup, "start": start, "expiry": expiry},
        ).fetchone()
        sub_id = sub["id"]

        # draft -> quotation
        res = transition(c, sub_id, "quotation", actor_id=1, expected_version=1)
        assert res["status"] == "quotation"
        assert res["quote_sent_on"] is not None
        assert res["quote_valid_until"] is not None
        assert res["version"] == 2

        # Stale version raises 409
        with pytest.raises(HTTPException) as exc:
            transition(c, sub_id, "confirmed", actor_id=1, expected_version=1)
        assert exc.value.status_code == 409

        # quotation -> confirmed
        res = transition(c, sub_id, "confirmed", actor_id=1, expected_version=2)
        assert res["status"] == "confirmed"

        # confirmed -> active
        res = transition(c, sub_id, "active", actor_id=1)
        assert res["status"] == "active"

        # Invalid transition: active -> quotation raises 409
        with pytest.raises(HTTPException) as exc:
            transition(c, sub_id, "quotation", actor_id=1)
        assert exc.value.status_code == 409


def test_pause_and_resume():
    with conn() as c:
        setup = create_customer_plan_term(c)
        sub = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(plan_id)s, '2026-01-01', '2026-12-31', %(pt_id)s, 'active')
            RETURNING id
            """,
            setup,
        ).fetchone()
        sub_id = sub["id"]

        actions = allowed_actions(c, sub_id, "admin")
        assert "pause" in actions

        pause(c, sub_id, actor_id=1)
        row = c.execute("SELECT is_paused FROM subscriptions WHERE id = %(id)s", {"id": sub_id}).fetchone()
        assert row["is_paused"]

        actions = allowed_actions(c, sub_id, "admin")
        assert "resume" in actions

        resume(c, sub_id, actor_id=1)
        row = c.execute("SELECT is_paused FROM subscriptions WHERE id = %(id)s", {"id": sub_id}).fetchone()
        assert not row["is_paused"]


def test_plan_flags_enforced():
    with conn() as c:
        setup = create_customer_plan_term(c)
        sub = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(strict_plan_id)s, '2026-01-01', '2026-12-31', %(pt_id)s, 'active')
            RETURNING id
            """,
            setup,
        ).fetchone()
        sub_id = sub["id"]

        with pytest.raises(HTTPException) as exc:
            pause(c, sub_id, actor_id=1)
        assert exc.value.status_code == 409

        with pytest.raises(HTTPException) as exc:
            renew(c, sub_id, actor_id=1)
        assert exc.value.status_code == 409

        with pytest.raises(HTTPException) as exc:
            close(c, sub_id, actor_id=1, reason="Test")
        assert exc.value.status_code == 409


def test_renew():
    with conn() as c:
        setup = create_customer_plan_term(c)
        sub = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(plan_id)s, '2026-01-01', '2026-01-31', %(pt_id)s, 'active')
            RETURNING id
            """,
            setup,
        ).fetchone()
        sub_id = sub["id"]

        renew(c, sub_id, actor_id=1)
        row = c.execute("SELECT expiry_date FROM subscriptions WHERE id = %(id)s", {"id": sub_id}).fetchone()
        assert row["expiry_date"] == date(2026, 3, 2)


def test_run_daily_auto_activate_and_auto_close():
    with conn() as c:
        setup = create_customer_plan_term(c)
        due = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(plan_id)s, '2026-02-01', '2026-12-31', %(pt_id)s, 'confirmed')
            RETURNING id
            """,
            setup,
        ).fetchone()

        expired = c.execute(
            """
            INSERT INTO subscriptions (customer_id, plan_id, start_date, expiry_date, payment_term_id, status)
            VALUES (%(cust_id)s, %(strict_plan_id)s, '2025-01-01', '2025-12-31', %(pt_id)s, 'active')
            RETURNING id
            """,
            setup,
        ).fetchone()

    res = run_daily(as_of=date(2026, 2, 5))
    assert res["activated"] >= 1
    assert res["closed"] >= 1

    with conn() as c:
        row_due = c.execute("SELECT status FROM subscriptions WHERE id = %(id)s", {"id": due["id"]}).fetchone()
        assert row_due["status"] == "active"

        row_exp = c.execute("SELECT status FROM subscriptions WHERE id = %(id)s", {"id": expired["id"]}).fetchone()
        assert row_exp["status"] == "closed"
