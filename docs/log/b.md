# Log — B (engine)

Append-only, newest at the bottom. Format: BUILD_PLAN §6.

## 2026-10-31 13:02 IST — B — B-02 — DONE
- Did: Implemented pure pricing engine matching §12 contract and types with D-02 half-up rounding, D-03 inclusive/exclusive tax, largest-remainder discount allocation, and calc_trace.
- Files: app/domain/pricing.py, tests/engine/test_pricing.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-04
- Needs from others: none
