"""The one source of business time (X-CLK-01).

Real mode returns the business-timezone date; simulated mode returns the
stored simulated date. Nothing else in app/ or scripts/ may read the wall
clock (tests/base/test_time_ban.py enforces it).
"""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.audit import audit
from app.config import settings
from app.db import conn, fetch_one

SIMULATED = "simulated"
REAL = "real"


def _real_today() -> date:
    return datetime.now(ZoneInfo(settings.business_tz)).date()  # real-time-ok: the clock


def now() -> datetime:
    """Current UTC timestamp, aware. For audit stamps and token expiry only."""
    return datetime.now(UTC)  # real-time-ok: the clock


def get_state() -> dict:
    """Return {'mode', 'today', 'simulated_today', 'updated_at'}."""
    row = fetch_one(
        "SELECT mode, simulated_today, updated_at FROM clock_state WHERE id = 1"
    )
    if row is None:
        raise RuntimeError("clock_state row is missing; run migrations")
    simulated_today = row["simulated_today"]
    if row["mode"] == SIMULATED and simulated_today is not None:
        today = simulated_today
    else:
        today = _real_today()
    return {
        "mode": str(row["mode"]),
        "today": today,
        "simulated_today": simulated_today,
        "updated_at": row["updated_at"],
    }


def today() -> date:
    return get_state()["today"]


def add_months(day: date, months: int) -> date:
    """Calendar-month arithmetic anchored on the day, clamped to month end."""
    month_index = day.month - 1 + int(months)
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _write_state(
    c,
    new_mode: str,
    new_today: date | None,
    actor_id: int | None,
    action: str,
) -> None:
    before = c.execute(
        "SELECT mode, simulated_today FROM clock_state WHERE id = 1 FOR UPDATE"
    ).fetchone()
    c.execute(
        "UPDATE clock_state SET mode = %s, simulated_today = %s, updated_at = %s WHERE id = 1",
        (new_mode, new_today, now()),
    )
    audit(
        c,
        actor_id,
        action,
        "clock_state",
        1,
        before={
            "mode": before["mode"],
            "simulated_today": str(before["simulated_today"]) if before["simulated_today"] else None,
        },
        after={
            "mode": new_mode,
            "simulated_today": str(new_today) if new_today else None,
        },
    )


def _run_daily(new_today: date, actor_id: int | None) -> None:
    if not settings.demo_mode:
        return
    from app.services.lifecycle import run_daily

    run_daily(new_today, actor_id)


def advance(days: int = 0, months: int = 0, actor_id: int | None = None) -> date:
    """Move the simulated date forward (months first, then days) and return it."""
    state = get_state()
    base = state["today"]
    target = add_months(base, months) if months else base
    target = target + timedelta(days=int(days))
    with conn() as c:
        _write_state(c, SIMULATED, target, actor_id, "clock.advance")
    _run_daily(target, actor_id)
    return target


def set_simulated(day: date, actor_id: int | None = None) -> None:
    """Jump to a specific simulated date."""
    with conn() as c:
        _write_state(c, SIMULATED, day, actor_id, "clock.set_simulated")
    _run_daily(day, actor_id)


def reset(actor_id: int | None = None) -> None:
    """Return to the real business date."""
    with conn() as c:
        _write_state(c, REAL, None, actor_id, "clock.reset")
