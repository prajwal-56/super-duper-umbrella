"""Expected billing periods (pure domain). Owner: B. Created as a contract stub by A.

Signature is fixed by BUILD_PLAN §12; change it only through a contract-change issue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Period:
    index: int
    start: date
    end: date
    paused: bool = False


def expected_periods(
    start: date,
    expiry: date,
    unit: str,
    count: int,
    as_of: date,
    closed_on: date | None,
    pauses: list[tuple[date, date | None]],
    cap: int = 36,
) -> list[Period]:
    """Return the periods a subscription should have been billed for, oldest first.

    Period k is [start + k*step, start + (k+1)*step - 1 day], computed from the
    anchor (never iteratively), clamped at month ends (D-05). Periods are
    included while period_start <= expiry (and <= closed_on when closed) and
    period_start <= as_of. Periods that start inside a pause window are
    returned with paused=True (D-08). At most `cap` periods are returned.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
