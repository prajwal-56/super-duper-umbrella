"""Billing engine entry points (database logic). Owner: B. Created as a contract stub by A."""

from __future__ import annotations

import psycopg


def bill_subscription(
    conn: psycopg.Connection,
    subscription_id: int,
    as_of,
    actor_id: int | None,
    run_id: int | None = None,
    auto_confirm: bool = False,
) -> list[int]:
    """Bill every missing period of one subscription inside the caller's transaction.

    Returns the invoice ids created. Periods are derived from facts (D-25);
    discounts are claimed atomically (D-11); duplicate periods are blocked by
    the partial unique index. Each invoice line stores its calc_trace.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def run_billing(
    as_of,
    mode: str,
    actor_id: int | None,
    auto_confirm: bool = False,
    subscription_ids: list[int] | None = None,
) -> int:
    """Run billing over all candidates and return the billing_runs.id (§13.3).

    mode is 'dry' or 'live'. Records one billing_run_items row per candidate
    with a dominant disposition, plus the run counts and integrity summary.
    Dry mode runs the same code path and rolls each subscription back.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
