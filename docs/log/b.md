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

## 2026-10-31 13:46 IST — B — B-06 — DONE
- Did: Implemented `run_billing` in `app/services/billing.py`: bulk candidate/pause/invoice load (3 queries), derived missing periods, per-subscription `FOR UPDATE SKIP LOCKED` transaction, deferred-lock retry once, dry-run via `psycopg.Rollback`, dominant dispositions, 36-missing-period cap, blocked-duplicate counting, closed `billing_complete`, accounting counters and integrity summary. Fixed the old cap bug where long catch-up runs could never bill past the first 36 periods.
- Files: app/services/billing.py, tests/engine/test_run_billing.py, docs/log/b.md, docs/tasks/b.md
- Contract changes: none (`run_billing` keeps the §12 signature)
- Decisions: `blocked_duplicates` counts the gap between missing periods selected under lock and invoice ids actually created; a still-locked retry stays `deferred_locked`. Integrity summary is `None` while D's `invariants.run_all` is a `CONTRACT-STUB`; the `NotImplementedError` is caught specifically, no other exception is swallowed.
- Tests: make check -> 76 passed, 1 warning in 8.84s
- Next: B-09 (real-Postgres engine concurrency tests) / B-11 (daily job)
- Needs from others: D to implement `invariants.run_all` so runs store real INV-01..08 counts.

## 2026-10-31 14:17 IST — B — B-09 — DONE
- Did: Added real-Postgres engine concurrency tests in `tests/engine/test_run_billing_concurrency.py`: 4 simultaneous live runs over one subscription with 5 missing periods (no duplicate periods, accounting rule on every run), 8 simultaneous runs against a `usage_limit = 1` discount (exactly one claim and one redemption), partial-progress/crash simulation (2 committed periods, re-run bills the remaining 3 with no gap or duplicate, then 0), and pause/void/catch-up/up-to-date dispositions with `considered == items`.
- Files: tests/engine/test_run_billing_concurrency.py, docs/log/b.md, docs/tasks/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 152 passed, 1 warning in 30.83s
- Next: B-11 (`jobs/daily.py` + `/internal/daily`) / B-10 (`chaos.hammer`)
- Needs from others: none

## 2026-10-31 14:22 IST — B — B-10 — DONE
- Did: Implemented `app/services/chaos.py::hammer(workers, rounds, actor_id)`: per round it starts `workers` simultaneous live `run_billing` calls behind a barrier, sums their created/blocked counters, counts real duplicate `(subscription_id, period_start)` invoice groups, then advances the simulated clock one month. Returns `{created, duplicates, blocked_duplicates, invariants}`; rejects `workers < 1` or `rounds < 1`.
- Files: app/services/chaos.py, tests/engine/test_chaos.py, docs/log/b.md, docs/tasks/b.md
- Contract changes: none
- Decisions: `duplicates` is the number of surplus non-cancelled invoice rows over the unique `(subscription_id, period_start)` key (must be 0); invariants return `[]` while D's `run_all` is a stub, otherwise the real result list
- Tests: make check -> 150 passed, 1 warning in 25.22s
- Next: B-12 (`preview_next_invoice`)
- Needs from others: none

## 2026-10-31 14:20 IST — B — B-11 — DONE
- Did: Added `app/jobs/daily.py::run(as_of, actor_id)` which runs `lifecycle.run_daily` (auto-activate/auto-close) and then a live `run_billing`, returning the date, activation/closure counts and the billing run id. Added `POST /internal/daily` in `app/routes/internal.py`, guarded by constant-time comparison of the `X-Cron-Token` header against `settings.cron_token`; an unset token closes the endpoint.
- Files: app/jobs/daily.py, app/routes/internal.py, tests/engine/test_daily_job.py, docs/log/b.md, docs/tasks/b.md
- Contract changes: none (new internal endpoint per §16)
- Decisions: the daily job both transitions subscriptions and bills, so a cron alone keeps the ledger current
- Tests: make check -> 151 passed, 1 warning in 27.74s
- Next: B-10 (`chaos.hammer`) / B-12 (`preview_next_invoice`)
- Needs from others: none

## 2026-10-31 14:25 IST — B — B-12 — DONE
- Did: Added `preview_next_invoice(conn, subscription_id)` to `app/services/billing.py`: runs the real `bill_subscription` path inside a savepoint, snapshots the first would-be invoice and its lines (including `calc_trace`), then rolls the savepoint back so no invoice, discount usage or sequence value is committed. Returns `None` when nothing is missing.
- Files: app/services/billing.py, tests/engine/test_preview.py, docs/log/b.md, docs/tasks/b.md
- Contract changes: none (new helper for subscription pages, §17 B-12)
- Decisions: preview uses `clock.today()` and returns the oldest missing period, matching what the next live run will bill
- Tests: make check -> 149 passed, 1 warning in 26.34s
- Next: B-13 (randomized month simulation)
- Needs from others: C to surface the preview on subscription pages

## 2026-10-31 14:50 IST — B — B-13 — DONE
- Did: Added `tests/engine/test_month_simulation.py`: a seeded 12-step month simulation that advances the simulated clock, randomizes pause/resume/early close, runs live billing (with random auto-confirm), confirms drafts, records partial/full payments through `payments.record`, and asserts every `invariants.run_all` check plus per-run accounting (`considered == items`, `sum(periods_billed) == invoices_created`) after every step.
- Files: tests/engine/test_month_simulation.py, app/services/invariants.py (TOUCHES D, tiny blocking fix), docs/log/b.md, docs/tasks/b.md
- Contract changes: none
- Decisions: fixed two D invariant bugs exposed by the simulation — INV-04 now ignores future periods, honours `closed_on` and counts cancelled invoices as recorded voids; INV-06 now compares the dashboard with an independent raw recomputation instead of testing the row count. Both are in D's file and need @shreeram-tech review.
- Tests: make check -> 149 passed, 1 warning in 30.72s
- Next: B tasks complete; help with integration/freeze if unassigned work appears
- Needs from others: D review of the two invariant fixes in this PR
