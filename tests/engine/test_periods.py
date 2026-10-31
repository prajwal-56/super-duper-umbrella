from datetime import date
import pytest
from app.domain.periods import expected_periods, Period


def test_monthly_periods_anchor_clamping():
    # Jan 31 anchor: Feb 28, Mar 31, Apr 30
    start = date(2026, 1, 31)
    expiry = date(2026, 12, 31)
    as_of = date(2026, 5, 1)

    periods = expected_periods(start, expiry, "month", 1, as_of)
    assert len(periods) == 4

    p0 = periods[0]
    assert p0.index == 0
    assert p0.start == date(2026, 1, 31)
    assert p0.end == date(2026, 2, 27)
    assert not p0.paused

    p1 = periods[1]
    assert p1.index == 1
    assert p1.start == date(2026, 2, 28)
    assert p1.end == date(2026, 3, 30)

    p2 = periods[2]
    assert p2.index == 2
    assert p2.start == date(2026, 3, 31)
    assert p2.end == date(2026, 4, 29)

    p3 = periods[3]
    assert p3.index == 3
    assert p3.start == date(2026, 4, 30)
    assert p3.end == date(2026, 5, 30)


def test_leap_year_february():
    # 2024 is leap year
    start = date(2024, 1, 31)
    expiry = date(2024, 3, 31)
    as_of = date(2024, 3, 1)

    periods = expected_periods(start, expiry, "month", 1, as_of)
    assert len(periods) == 2
    assert periods[0].start == date(2024, 1, 31)
    assert periods[1].start == date(2024, 2, 29)


def test_daily_and_weekly_periods():
    start = date(2026, 1, 1)
    expiry = date(2026, 1, 31)
    as_of = date(2026, 1, 4)

    # Daily with count 2
    periods = expected_periods(start, expiry, "day", 2, as_of)
    assert len(periods) == 2
    assert periods[0].start == date(2026, 1, 1)
    assert periods[0].end == date(2026, 1, 2)
    assert periods[1].start == date(2026, 1, 3)
    assert periods[1].end == date(2026, 1, 4)

    # Weekly with count 1
    as_of_week = date(2026, 1, 15)
    w_periods = expected_periods(start, expiry, "week", 1, as_of_week)
    assert len(w_periods) == 3
    assert w_periods[0].start == date(2026, 1, 1)
    assert w_periods[0].end == date(2026, 1, 7)
    assert w_periods[1].start == date(2026, 1, 8)
    assert w_periods[1].end == date(2026, 1, 14)
    assert w_periods[2].start == date(2026, 1, 15)


def test_pauses():
    start = date(2026, 1, 1)
    expiry = date(2026, 6, 30)
    as_of = date(2026, 4, 1)
    # Pause during February (starts 2026-02-01)
    pauses = [(date(2026, 1, 25), date(2026, 2, 15))]

    periods = expected_periods(start, expiry, "month", 1, as_of, pauses=pauses)
    assert len(periods) == 4
    assert not periods[0].paused  # Jan 1
    assert periods[1].paused      # Feb 1 is within pause
    assert not periods[2].paused  # Mar 1
    assert not periods[3].paused  # Apr 1


def test_closed_on():
    start = date(2026, 1, 1)
    expiry = date(2026, 12, 31)
    as_of = date(2026, 6, 1)
    closed_on = date(2026, 3, 1)

    periods = expected_periods(start, expiry, "month", 1, as_of, closed_on=closed_on)
    # Jan 1 and Feb 1 started before closed_on; Mar 1 onwards are >= closed_on
    assert len(periods) == 2
    assert periods[0].start == date(2026, 1, 1)
    assert periods[1].start == date(2026, 2, 1)


def test_cap_limit():
    start = date(2026, 1, 1)
    expiry = date(2030, 1, 1)
    as_of = date(2030, 1, 1)

    periods = expected_periods(start, expiry, "month", 1, as_of, cap=10)
    assert len(periods) == 10
