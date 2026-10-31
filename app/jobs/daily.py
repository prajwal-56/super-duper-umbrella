"""Daily scheduled work (owner: B)."""

from __future__ import annotations

from datetime import date

from app.clock import today
from app.services.billing import run_billing
from app.services.lifecycle import run_daily


def run(as_of: date | None = None, actor_id: int | None = None) -> dict[str, object]:
    """Auto-activate/auto-close subscriptions, then bill every due period."""
    if as_of is None:
        as_of = today()
    lifecycle = run_daily(as_of, actor_id)
    run_id = run_billing(as_of, "live", actor_id)
    return {
        "as_of": as_of.isoformat(),
        "activated": lifecycle["activated"],
        "closed": lifecycle["closed"],
        "billing_run_id": run_id,
    }
