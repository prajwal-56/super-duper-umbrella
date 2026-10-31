from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from app.db import conn
from app.services.billing import bill_subscription, run_billing


def _base(c):
    user = c.execute(
        "INSERT INTO users (email, password_hash, role) VALUES ('engine@example.com', 'hash', 'admin') RETURNING id"
    ).fetchone()
    cust = c.execute(
        "INSERT INTO customers (name, email) VALUES ('Engine Co', 'engine-co@example.com') RETURNING id"
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
        VALUES ('Seat', 'service', 20000, %(tax)s)
        RETURNING id
        """,
        {"tax": tax["id"]},
    ).fetchone()
    plan = c.execute(
        """
        INSERT INTO plans (name, billing_interval, interval_count, price_minor)
        VALUES ('Monthly', 'month', 1, 0)
        RETURNING id
        """
    ).fetchone()
    return {
        "user_id": user["id"],
        "cust_id": cust["id"],
        "pt_id": terms["id"],
        "tax_id": tax["id"],
        "prod_id": product["id"],
        "plan_id": plan["id"],
    }


def _sub(c, base, *, start="2026-01-01", expiry="2026-06-30", status="active",
         paused_from=None, plan_id=None):
    sub = c.execute(
        """
        INSERT INTO subscriptions (
            customer_id, plan_id, start_date, expiry_date, payment_term_id,
            status, is_paused
        ) VALUES (
            %(cust)s, %(plan)s, %(start)s, %(expiry)s, %(pt)s,
            %(status)s, %(paused)s
        ) RETURNING id
        """,
        {
            "cust": base["cust_id"],
            "plan": plan_id or base["plan_id"],
            "start": start,
            "expiry": expiry,
            "pt": base["pt_id"],
            "status": status,
            "paused": paused_from is not None,
        },
    ).fetchone()
    sub_id = sub["id"]
    c.execute(
        """
        INSERT INTO subscription_lines (
            subscription_id, product_id, quantity, unit_price_minor,
            tax_id, tax_rate_bps, tax_inclusive
        ) VALUES (
            %(sub)s, %(prod)s, 1, 20000, %(tax)s, 1800, false
        )
        """,
        {"sub": sub_id, "prod": base["prod_id"], "tax": base["tax_id"]},
    )
    if paused_from is not None:
        c.execute(
            "INSERT INTO subscription_pauses (subscription_id, paused_on) VALUES (%(s)s, %(p)s)",
            {"s": sub_id, "p": paused_from},
        )
    return sub_id


def _run_live(as_of, actor_id, barrier=None):
    if barrier is not None:
        barrier.wait()
    return run_billing(as_of=as_of, mode="live", actor_id=actor_id)


def _run_accounting(c, run_id):
    run = c.execute(
        "SELECT * FROM billing_runs WHERE id = %(id)s", {"id": run_id}
    ).fetchone()
    items = c.execute(
        "SELECT * FROM billing_run_items WHERE run_id = %(id)s", {"id": run_id}
    ).fetchall()
    assert run["status"] == "completed"
    assert run["considered"] == len(items)
    assert sum(item["periods_billed"] for item in items) == run["invoices_created"]
    return run, items


def _assert_no_duplicate_periods(c):
    duplicates = c.execute(
        """
        SELECT subscription_id, period_start, COUNT(*) AS n
          FROM invoices
         WHERE status <> 'cancelled'
         GROUP BY subscription_id, period_start
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    assert duplicates == []


def _invoice_count(c, sub_id):
    return c.execute(
        "SELECT COUNT(*) AS n FROM invoices WHERE subscription_id = %(id)s",
        {"id": sub_id},
    ).fetchone()["n"]


def test_four_concurrent_live_runs_have_no_duplicates():
    as_of = date(2026, 5, 15)
    with conn() as c:
        base = _base(c)
        sub_id = _sub(c, base)

    barrier = Barrier(4)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(_run_live, as_of, base["user_id"], barrier)
            for _ in range(4)
        ]
        run_ids = [future.result() for future in futures]

    with conn() as c:
        created = 0
        for run_id in run_ids:
            run, _ = _run_accounting(c, run_id)
            created += run["invoices_created"]
        assert created == 5
        assert _invoice_count(c, sub_id) == 5
        _assert_no_duplicate_periods(c)


def test_discount_usage_limit_race_claims_exactly_once():
    as_of = date(2026, 1, 15)
    with conn() as c:
        base = _base(c)
        sub_id = _sub(c, base)
        discount = c.execute(
            """
            INSERT INTO discounts (
                name, kind, value, starts_on, ends_on, scope, usage_limit, auto_apply
            ) VALUES (
                'One-shot', 'percent', 1000, '2026-01-01', '2026-12-31',
                'subscription', 1, true
            ) RETURNING id
            """
        ).fetchone()

    barrier = Barrier(8)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(_run_live, as_of, base["user_id"], barrier)
            for _ in range(8)
        ]
        run_ids = [future.result() for future in futures]

    with conn() as c:
        for run_id in run_ids:
            _run_accounting(c, run_id)
        usage = c.execute(
            "SELECT usage_count FROM discounts WHERE id = %(id)s",
            {"id": discount["id"]},
        ).fetchone()["usage_count"]
        redemptions = c.execute(
            "SELECT COUNT(*) AS n FROM discount_redemptions WHERE discount_id = %(id)s",
            {"id": discount["id"]},
        ).fetchone()["n"]
        assert usage == 1
        assert redemptions == 1
        assert _invoice_count(c, sub_id) == 1
        _assert_no_duplicate_periods(c)


def test_partial_progress_then_rerun_leaves_no_gap_or_duplicate():
    as_of = date(2026, 2, 15)
    later = date(2026, 5, 15)
    with conn() as c:
        base = _base(c)
        sub_id = _sub(c, base)

    # Simulate a crashed run that committed two per-subscription transactions.
    with conn() as c:
        early = bill_subscription(c, sub_id, as_of=as_of, actor_id=base["user_id"])
    assert len(early) == 2

    run_id = run_billing(as_of=later, mode="live", actor_id=base["user_id"])
    with conn() as c:
        run, items = _run_accounting(c, run_id)
        assert run["invoices_created"] == 3
        assert items[0]["periods_billed"] == 3
        assert _invoice_count(c, sub_id) == 5
        starts = [
            row["period_start"]
            for row in c.execute(
                "SELECT period_start FROM invoices WHERE subscription_id = %(id)s ORDER BY period_start",
                {"id": sub_id},
            ).fetchall()
        ]
        assert starts == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
            date(2026, 4, 1),
            date(2026, 5, 1),
        ]
        _assert_no_duplicate_periods(c)

    rerun = run_billing(as_of=later, mode="live", actor_id=base["user_id"])
    with conn() as c:
        run, _ = _run_accounting(c, rerun)
        assert run["invoices_created"] == 0
        assert _invoice_count(c, sub_id) == 5


def test_dispositions_cover_pause_void_and_catch_up():
    as_of = date(2026, 4, 15)
    with conn() as c:
        base = _base(c)
        catch_up = _sub(c, base)
        voided = _sub(c, base)
        paused = _sub(c, base, paused_from="2026-01-01")
        up_to_date = _sub(c, base)

        bill_subscription(c, voided, as_of=as_of, actor_id=base["user_id"])
        c.execute(
            "UPDATE invoices SET status = 'cancelled' WHERE subscription_id = %(id)s AND period_start = '2026-01-01'",
            {"id": voided},
        )
        bill_subscription(c, up_to_date, as_of=as_of, actor_id=base["user_id"])

    run_id = run_billing(as_of=as_of, mode="live", actor_id=base["user_id"])

    with conn() as c:
        run, items = _run_accounting(c, run_id)
        dispositions = {item["subscription_id"]: item["disposition"] for item in items}
        assert dispositions[catch_up] == "billed"
        assert dispositions[voided] == "skipped_period_voided"
        assert dispositions[paused] == "skipped_paused"
        assert dispositions[up_to_date] == "up_to_date"
        assert run["considered"] == 4
        _assert_no_duplicate_periods(c)
