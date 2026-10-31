# Log — B (engine)

Append-only, newest at the bottom. Format: BUILD_PLAN §6.

## 2026-10-31 13:04 IST — B — B-03 — DONE
- Did: Implemented pure discount selection `select(lines, candidates, as_of)` matching §12 contract and types with D-11 eligibility, best-per-line and one-subscription-scope selection.
- Files: app/domain/discounts.py, tests/engine/test_discounts.py, docs/log/b.md
- Contract changes: none
- Decisions: none
- Tests: make check -> 49 passed, 0 errors
- Next: B-07
- Needs from others: none
