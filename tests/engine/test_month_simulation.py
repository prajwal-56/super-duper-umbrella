import random
from datetime import date

from app import clock
from app.db import conn
from app.services import invoices, lifecycle, payments
from app.services.billing import run_billing
from app.services.invariants import run_all

SEED = 20261031
STEPS = 12


def _setup(c):
    user = c.execute(
        "INSERT INTO users (email, password_hash, role) VALUES ('sim@example.com', 'hash', 'admin') RETURNING id"
    ).fetchone()
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Simulation Co', 'sim-co@example.com') RETURNING id"
    ).fetchone()
    terms = c.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
    ).fetchone()
    tax = c.execute(
        "INSERT INTO taxes (name, rate_bps, inclusive) VALUES ('GST 18%', 1800, false) RETURNING id"
    ).fetchone()
    product = c.execute(
        """
        INSERT INTO products (name, type, sales_price_minor, tax_id)
        VALUES ('Seat', 'service', 20000, %(tax)s) RETURNING id
        """,
        {"tax": tax["id"]},
    ).fetchone()
    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, price_minor)
        VALUES ('Monthly', 'month', 1, 0) RETURNING id
        """
    ).fetchone()
    sub = c.execute(
        """
        INSERT INTO subscriptions (
            customer_id, plan_id, start_date, expiry_date, payment_term_id, status
        ) VALUES (
            %(cust)s, %(plan)s, '2026-01-01', '2026-12-31', %(pt)s, 'active'
        ) RETURNING id
        """,
        {"cust": cust["id"], "plan": plan["id"], "pt": terms["id"]},
    ).fetchone()
    sub_id = sub["id"]
    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor,
            tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (%(sub)s, %(prod)s, 2, 20000, %(tax)s, 1800, false)
        """,
        {"sub": sub_id, "prod": product["id"], "tax": tax["id"]},
    )
    c.execute(
        """
        INSERT INTO discounts (
            name, kind, value, starts_on, ends_on, scope, usage_limit, auto_apply
        ) VALUES (
            'Sim discount', 'percent', 1000, '2026-01-01', '2026-12-31',
            'subscription', 4, true
        )
        """
    )
    return user["id"], sub_id


def _subscription_state(sub_id):
    with conn() as c:
        return c.execute(
            "SELECT status, is_paused FROM subscriptions WHERE id = %(id)s",
            {"id": sub_id},
        ).fetchone()


def _pause_or_resume(rng, sub_id, actor_id):
    row = _subscription_state(sub_id)
    if row["status"] != "active":
        return
    if not row["is_paused"] and rng.random() < 0.20:
        with conn() as c:
            lifecycle.pause(c, sub_id, actor_id)
    elif row["is_paused"] and rng.random() < 0.50:
        with conn() as c:
            lifecycle.resume(c, sub_id, actor_id)


def _maybe_close(rng, sub_id, actor_id, step):
    row = _subscription_state(sub_id)
    if row["status"] == "active" and step >= 4 and rng.random() < 0.10:
        with conn() as c:
            lifecycle.close(c, sub_id, actor_id, reason="Simulation close")


def _confirm_some_drafts(rng, actor_id):
    with conn() as c:
        draft_ids = [
            row["id"]
            for row in c.execute(
                "SELECT id FROM invoices WHERE status = 'draft' ORDER BY id"
            ).fetchall()
        ]
    for invoice_id in draft_ids:
        if rng.random() < 0.50:
            with conn() as c:
                invoices.confirm(c, invoice_id, actor_id)


def _pay_some_invoices(rng, actor_id):
    with conn() as c:
        rows = c.execute(
            """
            SELECT id, total_minor, amount_paid_minor
              FROM invoices
             WHERE status = 'confirmed' AND total_minor > amount_paid_minor
             ORDER BY id
            """
        ).fetchall()
    rng.shuffle(rows)
    for row in rows[: rng.randint(0, 3)]:
        outstanding = int(row["total_minor"]) - int(row["amount_paid_minor"])
        if rng.random() < 0.5:
            amount = outstanding
        else:
            amount = rng.randint(1, outstanding)
        with conn() as c:
            payments.record(
                c,
                row["id"],
                "cash",
                amount,
                clock.today(),
                None,
                actor_id,
            )


def _assert_invariants(step):
    with conn() as c:
        results = run_all(c)
        bad = [r for r in results if not r.ok]
        assert not bad, (
            f"step {step}: "
            + ", ".join(f"{r.id} ({r.violations}): {r.sample_rows}" for r in bad)
        )
        broken_runs = c.execute(
            """
            SELECT r.id
              FROM billing_runs r
              LEFT JOIN (
                    SELECT run_id, COUNT(*) AS item_count,
                           SUM(periods_billed) AS periods
                      FROM billing_run_items
                     GROUP BY run_id
                   ) i ON i.run_id = r.id
             WHERE r.considered != COALESCE(i.item_count, 0)
                OR r.invoices_created != COALESCE(i.periods, 0)
            """
        ).fetchall()
        assert broken_runs == []


def test_random_month_simulation_keeps_invariants_green():
    rng = random.Random(SEED)
    clock.set_simulated(date(2026, 1, 15), None)
    with conn() as c:
        actor_id, sub_id = _setup(c)

    for step in range(STEPS):
        months = rng.choice([0, 1, 1, 2])
        if months:
            clock.advance(months=months, actor_id=actor_id)

        _pause_or_resume(rng, sub_id, actor_id)
        run_billing(
            mode="live",
            actor_id=actor_id,
            auto_confirm=rng.random() < 0.50,
        )
        _maybe_close(rng, sub_id, actor_id, step)
        _confirm_some_drafts(rng, actor_id)
        _pay_some_invoices(rng, actor_id)
        _assert_invariants(step)

    with conn() as c:
        runs = c.execute("SELECT COUNT(*) AS n FROM billing_runs").fetchone()["n"]
        invoices_count = c.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"]
        payments_count = c.execute("SELECT COUNT(*) AS n FROM payments").fetchone()["n"]
        assert runs == STEPS
        assert invoices_count > 0
        assert payments_count > 0
