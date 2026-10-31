# Agent B — Log

## 2026-10-31 12:17 IST — B — B-01 — DONE
- Did: Implemented anchor-relative period derivation with month-end clamping, leap year support, pauses, closed_on, and cap limit.
- Files: app/domain/periods.py, tests/engine/test_periods.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: python3 -m pytest tests/engine/test_periods.py -> 6 passed in 0.11s
- Next: B-02
- Needs from others: none

## 2026-10-31 13:02 IST — B — B-02 — DONE
- Did: Implemented pure pricing engine matching §12 contract and types with D-02 half-up rounding, D-03 inclusive/exclusive tax, largest-remainder discount allocation, and calc_trace.
- Files: app/domain/pricing.py, tests/engine/test_pricing.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-04
- Needs from others: none

## 2026-10-31 13:03 IST — B — B-04 — DONE
- Did: Implemented pure state machines for subscriptions and invoices according to §13.4 and §11 using frozenset.
- Files: app/domain/state_machines.py, tests/engine/test_state_machines.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-03
- Needs from others: none

## 2026-10-31 13:04 IST — B — B-03 — DONE
- Did: Implemented pure discount selection `select(lines, candidates, as_of)` matching §12 contract and types with D-11 eligibility, best-per-line and one-subscription-scope selection.
- Files: app/domain/discounts.py, tests/engine/test_discounts.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-07
- Needs from others: none

## 2026-10-31 13:13 IST — B — B-07 — DONE
- Did: Implemented subscription lifecycle services in `app/services/lifecycle.py` (`transition`, `pause`, `resume`, `close`, `renew`, `allowed_actions`, `run_daily`) with optimistic concurrency, quote validity, plan flag enforcement, and audit rows.
- Files: app/services/lifecycle.py, tests/engine/test_lifecycle.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 66 passed, 1 warning in 5.71s
- Next: B-05 (bill_subscription)
- Needs from others: none

## 2026-10-31 13:20 IST — B — B-05 — DONE
- Did: Implemented `bill_subscription` in `app/services/billing.py` with derived expected periods, atomic discount claiming, savepoint rollbacks, calc_trace snapshots, auto-confirm option, and audit logging.
- Files: app/services/billing.py, tests/engine/test_bill_subscription.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 68 passed, 1 warning in 5.88s
- Next: B-06 (run_billing)
- Needs from others: none
