"""Append-only audit trail. Every state change and money-affecting write calls audit()."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb


def audit(
    conn: psycopg.Connection,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: int,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Insert one row into audit_log inside the caller's transaction.

    `before` and `after` are stored as JSONB. The table is append-only
    (a trigger rejects UPDATE and DELETE).
    """
    conn.execute(
        """
        INSERT INTO audit_log (actor_id, action, entity, entity_id, before, after)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            actor_id,
            action,
            entity,
            entity_id,
            Jsonb(before) if before is not None else None,
            Jsonb(after) if after is not None else None,
        ),
    )
