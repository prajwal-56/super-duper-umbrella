"""Expected billing periods (pure domain). Owner: B.

Signature is fixed by BUILD_PLAN §12; change it only through a contract-change issue.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Period:
    index: int
    start: date
    end: date
    paused: bool = False


def _add_months_clamped(start: date, months: int) -> date:
    """
    Anchor-relative month addition with month-end clamping.
    E.g. Jan 31 + 1 month -> Feb 28 (or 29 in leap year).
    Jan 31 + 2 months -> Mar 31.
    """
    total_months = (start.year * 12 + (start.month - 1)) + months
    year = total_months // 12
    month = (total_months % 12) + 1
    max_day = calendar.monthrange(year, month)[1]
    day = min(start.day, max_day)
    return date(year, month, day)


def _step_anchor(start: date, k: int, unit: str, count: int) -> date:
    """Compute start + k * (count * unit) relative to initial anchor."""
    if unit == "day":
        return start + timedelta(days=k * count)
    elif unit == "week":
        return start + timedelta(days=k * count * 7)
    elif unit == "month":
        return _add_months_clamped(start, k * count)
    elif unit == "year":
        return _add_months_clamped(start, k * count * 12)
    else:
        raise ValueError(f"Unknown billing unit: {unit}")


def expected_periods(
    start: date,
    expiry: date,
    unit: str,
    count: int,
    as_of: date,
    closed_on: date | None = None,
    pauses: list[tuple[date, date | None]] | None = None,
    cap: int = 36,
) -> list[Period]:
    """
    Derive expected periods anchor-relative to start.
    Periods are in advance.
    Period k = [start + k*step, start + (k+1)*step - 1 day].
    Periods are generated while period_start <= expiry and period_start <= as_of.
    If closed_on is given, periods starting >= closed_on are not generated.
    Pause: if period_start falls inside [paused_on, resumed_on], paused=True.
    (If resumed_on is None, pause is open-ended).
    Up to cap periods are returned.
    """
    if pauses is None:
        pauses = []

    periods: list[Period] = []
    k = 0

    while len(periods) < cap:
        p_start = _step_anchor(start, k, unit, count)
        p_next_start = _step_anchor(start, k + 1, unit, count)
        p_end = p_next_start - timedelta(days=1)

        # Expiry rule: periods are included while period_start <= expiry
        if p_start > expiry:
            break

        # as_of rule: only periods that have started as of as_of are due/expected to be billed
        if p_start > as_of:
            break

        # Early close rule: D-19: early close stops future periods.
        # Periods that started before the close date still get billed.
        # So if closed_on is set, periods starting >= closed_on are not generated.
        if closed_on is not None and p_start >= closed_on:
            break

        # Check pause: D-08: periods that START inside a pause window are not billed / paused
        is_paused = False
        for p_pause_start, p_pause_end in pauses:
            if p_pause_end is None:
                if p_start >= p_pause_start:
                    is_paused = True
                    break
            else:
                if p_pause_start <= p_start <= p_pause_end:
                    is_paused = True
                    break

        periods.append(Period(index=k, start=p_start, end=p_end, paused=is_paused))
        k += 1

    return periods
