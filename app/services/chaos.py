"""Concurrency hammer (Tier 1). Owner: B."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app import clock
from app.db import conn
from app.services.billing import run_billing
from app.services.invariants import run_all


def _duplicate_periods() -> int:
    with conn() as c:
        row = c.execute(
            """
            SELECT COALESCE(SUM(n - 1), 0) AS duplicates
              FROM (
                    SELECT COUNT(*) AS n
                      FROM invoices
                     WHERE status <> 'cancelled'
                     GROUP BY subscription_id, period_start
                    HAVING COUNT(*) > 1
                   ) AS dup
            """
        ).fetchone()
        return int(row["duplicates"])


def _invariants() -> list[dict[str, object]]:
    with conn() as c:
        try:
            results = run_all(c)
        except NotImplementedError:
            return []
        return [
            {
                "id": result.id,
                "name": result.name,
                "ok": result.ok,
                "violations": result.violations,
            }
            for result in results
        ]


def hammer(workers: int, rounds: int, actor_id: int | None) -> dict:
    """Run `workers` concurrent live billing runs per round, advancing one month between rounds.

    Returns created invoices, duplicate periods found (must be 0), blocked
    duplicates, and the integrity-check results.
    """
    if workers < 1 or rounds < 1:
        raise ValueError("workers and rounds must both be at least 1")

    created = 0
    blocked = 0
    duplicates = 0

    for _ in range(rounds):
        barrier = Barrier(workers)

        def worker(gate: Barrier = barrier) -> int:
            gate.wait()
            return run_billing(mode="live", actor_id=actor_id)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            run_ids = [future.result() for future in [pool.submit(worker) for _ in range(workers)]]

        with conn() as c:
            rows = c.execute(
                "SELECT invoices_created, blocked_duplicates FROM billing_runs WHERE id = ANY(%(ids)s)",
                {"ids": run_ids},
            ).fetchall()
        created += sum(row["invoices_created"] for row in rows)
        blocked += sum(row["blocked_duplicates"] for row in rows)
        duplicates += _duplicate_periods()

        clock.advance(months=1, actor_id=actor_id)

    return {
        "created": created,
        "duplicates": duplicates,
        "blocked_duplicates": blocked,
        "invariants": _invariants(),
    }
