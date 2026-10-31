"""Simulated clock (X-CLK-01, D-05 month clamping)."""

from datetime import date

from app import clock
from app.db import conn


def test_real_mode_returns_business_date():
    state = clock.get_state()
    assert state["mode"] == "real"
    assert clock.today() == date.today()


def test_set_simulated_and_advance():
    clock.set_simulated(date(2026, 1, 31))
    assert clock.today() == date(2026, 1, 31)
    assert clock.get_state()["mode"] == "simulated"

    assert clock.advance(months=1) == date(2026, 2, 28)
    assert clock.today() == date(2026, 2, 28)

    assert clock.advance(days=1) == date(2026, 3, 1)


def test_advance_months_and_days_together():
    clock.set_simulated(date(2026, 1, 31))
    assert clock.advance(months=1, days=2) == date(2026, 3, 2)


def test_reset_returns_to_real():
    clock.set_simulated(date(2026, 1, 31))
    clock.reset()
    state = clock.get_state()
    assert state["mode"] == "real"
    assert state["simulated_today"] is None
    assert clock.today() == date.today()


def test_clock_changes_are_audited():
    clock.set_simulated(date(2026, 1, 31), actor_id=7)
    clock.advance(days=1, actor_id=7)
    with conn() as c:
        rows = c.execute(
            "SELECT action, actor_id FROM audit_log WHERE entity = 'clock_state' ORDER BY id"
        ).fetchall()
    assert [row["action"] for row in rows] == ["clock.set_simulated", "clock.advance"]
    assert all(row["actor_id"] == 7 for row in rows)


def test_add_months_clamps_to_month_end():
    assert clock.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert clock.add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert clock.add_months(date(2024, 2, 29), 12) == date(2025, 2, 28)
    assert clock.add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert clock.add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)
