# Tasks — B (engine)

Legend: `- [ ] B-01 (15) ...` — rough minutes. Tier 0 unless marked.

## Prep (T+0:00, no dependencies, pure code in `app/domain/`)

- [x] B-01 (15) `periods.py` (anchor-relative month/year math with month-end clamping, leap years, pauses, closed_on, cap) + tests.
- [x] B-02 (25) `pricing.py` and tax math (D-02, D-03, largest-remainder allocation, `calc_trace` that reconciles) + property tests (`sum(lines) == totals`, discount <= subtotal, never negative).
- [x] B-04 (10) `state_machines.py` tables + tests.
- [x] B-03 (15) `discounts.py` selection (eligibility, best-per-line, one subscription-scope, tie-breaks) + tests.

## After base-0a

- [x] B-07 (30) Tier 0: `lifecycle.py` (all transitions, plan flags, quote validity, optimistic version, pause history, renew, `allowed_actions`, `run_daily` auto-activate and auto-close) + tests.
- [x] B-05 (40) Tier 0: `bill_subscription` (§13.3 per-subscription logic, atomic discount claim, calc_trace stored, audit) + tests.
- [x] B-06 (40) Tier 0: `run_billing` (candidates, bulk load, dispositions, SKIP LOCKED, deferred retry, dry-run via rollback, accounting rule, integrity summary).
- [x] B-09 (30) Tier 0: engine tests on real Postgres: run 3x -> no duplicates; 4 concurrent threads; discount limit race (limit 1, 8 concurrent runs -> exactly 1 use); crash mid-run then re-run -> no gap/no duplicate; pause/void/catch-up dispositions; `considered == items`.
- [x] B-11 (10) Tier 1: `jobs/daily.py` + `/internal/daily` guarded by `CRON_TOKEN`.
- [x] B-10 (20) Tier 1: `chaos.hammer` (N concurrent live runs per round, advance the clock one period between rounds; returns created / duplicates found (must be 0) / blocked_duplicates / invariants).
- [ ] B-12 (15) Tier 1: `preview_next_invoice(conn, sub_id)` via dry-run for subscription pages.
- [ ] B-13 (30) Tier 2: randomized month-simulation test (random sequences of clock advances, runs, pauses, closes, payments; invariants checked after every step).
