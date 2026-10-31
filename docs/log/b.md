# Log — B (engine)

Append-only, newest at the bottom. Format: BUILD_PLAN §6.

## 2026-10-31 13:03 IST — B — B-04 — DONE
- Did: Implemented pure state machines for subscriptions and invoices according to §13.4 and §11 using frozenset.
- Files: app/domain/state_machines.py, tests/engine/test_state_machines.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-03
- Needs from others: none

## 2026-10-31 13:13 IST — B — B-07 — DONE
- Did: Implemented subscription lifecycle services in `app/services/lifecycle.py` (`transition`, `pause`, `resume`, `close`, `renew`, `allowed_actions`, `run_daily`) with optimistic concurrency, quote validity, plan flag enforcement, and audit rows.
- Files: app/services/lifecycle.py, tests/engine/test_lifecycle.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 66 passed, 1 warning in 5.71s
- Next: B-05 (bill_subscription)
- Needs from others: none
