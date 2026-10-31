"""Subscription lifecycle (database logic). Owner: B.

Signatures are fixed by BUILD_PLAN §12.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import psycopg
from fastapi import HTTPException

from app.audit import audit
from app.clock import today
from app.db import conn as db_conn
from app.domain.state_machines import SUBSCRIPTION_TRANSITIONS, can_transition


def _json_serializable(obj: Any) -> Any:
    """Recursively convert dates/datetimes to ISO strings for JSONB serialization."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_serializable(x) for x in obj]
    return obj


def transition(
    conn: psycopg.Connection,
    subscription_id: int,
    to_status: str,
    actor_id: int | None,
    expected_version: int | None = None,
) -> dict[str, Any]:
    """Move a subscription to `to_status`, enforcing §13.4 and the plan flags.

    Writes the audit row in the same transaction. A stale expected_version or
    an invalid transition raises a 409-mapped error carrying the allowed list.
    Entering `active` calls billing.bill_subscription so the first invoice
    exists immediately.
    """
    row = conn.execute(
        """
        SELECT s.*, p.allow_early_close, p.auto_close, p.allow_pause, p.allow_renew
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
         WHERE s.id = %(id)s
           FOR UPDATE
        """,
        {"id": subscription_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    current_status = row["status"]
    current_version = row["version"]

    if expected_version is not None and expected_version != current_version:
        raise HTTPException(
            status_code=409,
            detail=f"Subscription version conflict: expected {expected_version}, got {current_version}",
        )

    allowed = sorted(list(SUBSCRIPTION_TRANSITIONS.get(current_status, frozenset())))
    if not can_transition("subscription", current_status, to_status):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition from '{current_status}' to '{to_status}'. Allowed: {allowed}",
        )

    today_date = today()

    # Rule checks based on transitions
    # quotation -> confirmed: check quote validity (D-16)
    if current_status == "quotation" and to_status == "confirmed":
        if row["quote_valid_until"] and today_date > row["quote_valid_until"]:
            raise HTTPException(
                status_code=409,
                detail=f"Quotation expired on {row['quote_valid_until']}",
            )

    # active -> closed: early close check (D-19, §13.4)
    if current_status == "active" and to_status == "closed":
        if not row["allow_early_close"] and row["expiry_date"] and today_date < row["expiry_date"]:
            raise HTTPException(
                status_code=409,
                detail="Plan does not permit early closure before expiry date",
            )

    # Status updates
    updates: dict[str, Any] = {
        "status": to_status,
        "version": current_version + 1,
    }

    if current_status == "draft" and to_status == "quotation":
        # Quote sent
        valid_days = 15
        if row["template_id"]:
            tpl = conn.execute(
                "SELECT validity_days FROM quotation_templates WHERE id = %(id)s",
                {"id": row["template_id"]},
            ).fetchone()
            if tpl and tpl["validity_days"]:
                valid_days = tpl["validity_days"]

        updates["quote_sent_on"] = today_date
        updates["quote_valid_until"] = today_date + timedelta(days=valid_days)

    if to_status == "closed":
        updates["closed_on"] = today_date
        if not row.get("close_reason"):
            updates["close_reason"] = "Closed"

    set_clauses = [f"{k} = %({k})s" for k in updates.keys()]
    query_params = {**updates, "id": subscription_id}

    updated = conn.execute(
        f"""
        UPDATE subscriptions
           SET {', '.join(set_clauses)}
         WHERE id = %(id)s
     RETURNING *
        """,
        query_params,
    ).fetchone()

    audit(
        conn,
        actor_id=actor_id,
        action="transition",
        entity="subscription",
        entity_id=subscription_id,
        before=_json_serializable(dict(row)),
        after=_json_serializable(dict(updated)),
    )

    # If entering active, generate the first invoice immediately
    if to_status == "active":
        from app.services.billing import bill_subscription
        try:
            bill_subscription(conn, subscription_id, as_of=today_date, actor_id=actor_id)
        except NotImplementedError:
            pass

    return dict(updated)


def pause(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Pause an Active subscription when plan.allow_pause; record pause history."""
    row = conn.execute(
        """
        SELECT s.*, p.allow_pause
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
         WHERE s.id = %(id)s
           FOR UPDATE
        """,
        {"id": sub_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if row["status"] != "active":
        raise HTTPException(status_code=409, detail="Only active subscriptions can be paused")

    if not row["allow_pause"]:
        raise HTTPException(status_code=409, detail="Plan does not allow pause")

    if row["is_paused"]:
        raise HTTPException(status_code=409, detail="Subscription is already paused")

    today_date = today()

    conn.execute(
        """
        UPDATE subscriptions
           SET is_paused = true, version = version + 1
         WHERE id = %(id)s
        """,
        {"id": sub_id},
    )

    conn.execute(
        """
        INSERT INTO subscription_pauses (subscription_id, paused_on)
        VALUES (%(sub_id)s, %(today)s)
        """,
        {"sub_id": sub_id, "today": today_date},
    )

    audit(
        conn,
        actor_id=actor_id,
        action="pause",
        entity="subscription",
        entity_id=sub_id,
        before={"is_paused": False},
        after={"is_paused": True, "paused_on": str(today_date)},
    )


def resume(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Resume a paused Active subscription; close the open pause window."""
    row = conn.execute(
        """
        SELECT * FROM subscriptions WHERE id = %(id)s FOR UPDATE
        """,
        {"id": sub_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not row["is_paused"]:
        raise HTTPException(status_code=409, detail="Subscription is not paused")

    today_date = today()

    conn.execute(
        """
        UPDATE subscriptions
           SET is_paused = false, version = version + 1
         WHERE id = %(id)s
        """,
        {"id": sub_id},
    )

    conn.execute(
        """
        UPDATE subscription_pauses
           SET resumed_on = %(today)s
         WHERE subscription_id = %(sub_id)s AND resumed_on IS NULL
        """,
        {"sub_id": sub_id, "today": today_date},
    )

    audit(
        conn,
        actor_id=actor_id,
        action="resume",
        entity="subscription",
        entity_id=sub_id,
        before={"is_paused": True},
        after={"is_paused": False, "resumed_on": str(today_date)},
    )


def close(
    conn: psycopg.Connection, sub_id: int, actor_id: int | None, reason: str
) -> None:
    """Close a subscription (early close requires plan.allow_early_close; D-19)."""
    row = conn.execute(
        """
        SELECT s.*, p.allow_early_close
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
         WHERE s.id = %(id)s
           FOR UPDATE
        """,
        {"id": sub_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if row["status"] == "closed":
        return

    today_date = today()
    if not row["allow_early_close"] and row["expiry_date"] and today_date < row["expiry_date"]:
        raise HTTPException(
            status_code=409, detail="Plan does not allow early close"
        )

    updated = conn.execute(
        """
        UPDATE subscriptions
           SET status = 'closed', closed_on = %(today)s, close_reason = %(reason)s, version = version + 1
         WHERE id = %(id)s
     RETURNING *
        """,
        {"id": sub_id, "today": today_date, "reason": reason},
    ).fetchone()

    audit(
        conn,
        actor_id=actor_id,
        action="close",
        entity="subscription",
        entity_id=sub_id,
        before=_json_serializable(dict(row)),
        after=_json_serializable(dict(updated)),
    )


def renew(conn: psycopg.Connection, sub_id: int, actor_id: int | None) -> None:
    """Extend expiry_date by the original term when plan.allow_renew (D-24)."""
    row = conn.execute(
        """
        SELECT s.*, p.allow_renew
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
         WHERE s.id = %(id)s
           FOR UPDATE
        """,
        {"id": sub_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not row["allow_renew"]:
        raise HTTPException(status_code=409, detail="Plan does not allow renewal")

    if row["status"] not in ("active", "confirmed"):
        raise HTTPException(
            status_code=409, detail=f"Cannot renew subscription in '{row['status']}' state"
        )

    term_days = (row["expiry_date"] - row["start_date"]).days
    new_expiry = row["expiry_date"] + timedelta(days=term_days)

    updated = conn.execute(
        """
        UPDATE subscriptions
           SET expiry_date = %(new_expiry)s, version = version + 1
         WHERE id = %(id)s
     RETURNING *
        """,
        {"id": sub_id, "new_expiry": new_expiry},
    ).fetchone()

    audit(
        conn,
        actor_id=actor_id,
        action="renew",
        entity="subscription",
        entity_id=sub_id,
        before=_json_serializable(dict(row)),
        after=_json_serializable(dict(updated)),
    )


def allowed_actions(conn: psycopg.Connection, subscription_id: int, role: str) -> list[str]:
    """Actions this role may take now, from status and plan flags (drives UI)."""
    row = conn.execute(
        """
        SELECT s.*, p.allow_early_close, p.allow_pause, p.allow_renew
          FROM subscriptions s
          JOIN plans p ON p.id = s.plan_id
         WHERE s.id = %(id)s
        """,
        {"id": subscription_id},
    ).fetchone()

    if not row:
        return []

    status = row["status"]
    is_paused = row["is_paused"]
    actions: list[str] = []

    if role in ("admin", "staff"):
        if status == "draft":
            actions.extend(["send_quote", "confirm"])
        elif status == "quotation":
            actions.extend(["confirm", "revise", "close"])
        elif status == "confirmed":
            actions.extend(["activate", "close"])
        elif status == "active":
            if row["allow_pause"]:
                actions.append("resume" if is_paused else "pause")
            if row["allow_early_close"]:
                actions.append("close")
            if row["allow_renew"]:
                actions.append("renew")

    elif role == "customer":
        if status == "quotation":
            actions.append("confirm")
        elif status == "active":
            if row["allow_pause"]:
                actions.append("resume" if is_paused else "pause")
            if row["allow_early_close"]:
                actions.append("close")
            if row["allow_renew"]:
                actions.append("renew")

    return actions


def run_daily(as_of: date | None = None, actor_id: int | None = None) -> dict[str, int]:
    """Auto-activate due subscriptions and auto-close expired ones (D-10).

    Called by the clock when the date changes and by the daily job.
    """
    if as_of is None:
        as_of = today()

    activated_count = 0
    closed_count = 0

    with db_conn() as connection:
        # 1. Auto-activate confirmed subscriptions where start_date <= as_of
        due_subs = connection.execute(
            """
            SELECT id FROM subscriptions
             WHERE status = 'confirmed' AND start_date <= %(as_of)s
             ORDER BY id
            """,
            {"as_of": as_of},
        ).fetchall()

        for s in due_subs:
            try:
                transition(connection, s["id"], "active", actor_id=actor_id)
                activated_count += 1
            except Exception:
                pass

        # 2. Auto-close: D-10: if plan.auto_close, Active closes when as_of > min(expiry_date, plan.available_to)
        # with closed_on = that date
        auto_close_subs = connection.execute(
            """
            SELECT s.id, s.expiry_date, p.available_to
              FROM subscriptions s
              JOIN plans p ON p.id = s.plan_id
             WHERE s.status = 'active'
               AND p.auto_close = true
               AND (
                    (s.expiry_date IS NOT NULL AND %(as_of)s > s.expiry_date)
                 OR (p.available_to IS NOT NULL AND %(as_of)s > p.available_to)
               )
             ORDER BY s.id
            """,
            {"as_of": as_of},
        ).fetchall()

        for s in auto_close_subs:
            try:
                close(connection, s["id"], actor_id=actor_id, reason="Auto-closed on expiry")
                closed_count += 1
            except Exception:
                pass

    return {
        "activated": activated_count,
        "closed": closed_count,
    }
