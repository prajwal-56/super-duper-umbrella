"""Concurrency hammer (Tier 1). Owner: B. Created as a contract stub by A."""

from __future__ import annotations


def hammer(workers: int, rounds: int, actor_id: int | None) -> dict:
    """Run N concurrent live billing runs per round, advancing one period between rounds.

    Returns {'created': int, 'duplicates': int (must be 0), 'blocked_duplicates': int,
    'invariants': list}. Used by the billing-run page's "Hammer it" button.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B
