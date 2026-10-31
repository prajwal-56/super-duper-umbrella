"""Subscription lifecycle (database logic). Owner: B. Created as a contract stub by A.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

import psycopg


def transition(
    conn: psycopg.Connection,
    subscription_id: int,
    to_status: str,
    actor_id: int | None,
    expected_version: int | None = None,
) -> dict:
    """Move a subscription to `to_status`, enforcing §13.4 and the plan flags.

    Writes the audit row in the same transaction. A stale expected_version or
    an invalid transition raises a 409-mapped error carrying the allowed list.
    Entering `active` calls billing.bill_subscription so the first invoice
    exists immediately.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def pause(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Pause an Active subscription when plan.allow_pause; record pause history."""
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def resume(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Resume a paused Active subscription; close the open pause window."""
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def close(
    conn: psycopg.Connection, sub_id: int, actor_id: int | None, reason: str
) -> None:
    """Close a subscription (early close requires plan.allow_early_close; D-19)."""
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def renew(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Extend expiry_date by the original term when plan.allow_renew (D-24)."""
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def allowed_actions(conn: psycopg.Connection, subscription_id: int, role: str) -> list[str]:
    """Actions this role may take now, from status and plan flags (drives UI)."""
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B


def run_daily(as_of, actor_id: int | None = None) -> dict:
    """Auto-activate due subscriptions and auto-close expired ones (D-10).

    Called by the clock when the date changes and by the daily job.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
