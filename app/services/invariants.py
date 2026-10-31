"""Integrity checks (INV-01..08). Owner: D. Created as a contract stub by A.

The SQL in db/queries/ is written independently of the engine so a bug in the
Python cannot hide behind the same bug in the checker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import psycopg


@dataclass
class InvariantResult:
    id: str
    name: str
    ok: bool
    violations: int
    sample_rows: list[dict[str, Any]] = field(default_factory=list)


def run_all(conn: psycopg.Connection) -> list[InvariantResult]:
    """Run every integrity check and return one InvariantResult per check.

    Checks: no duplicate periods, invoice totals equal their lines, payments
    consistent, no missing periods, discount counters consistent, dashboard
    equals raw data, run accounting, calc traces reconcile (§13.7).
    """
    raise NotImplementedError("CONTRACT-STUB owner=D")  # CONTRACT-STUB owner=D
