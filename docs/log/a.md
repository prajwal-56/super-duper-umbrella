# Log — A (lead)

Append-only, newest at the bottom. Format: BUILD_PLAN §6.

## 2026-10-31 12:34 IST — A — A-01..A-05 — DONE
- Did: scaffolded the repo (Makefile, docker-compose Postgres 16, ruff, env); wrote the base schema + migration runner + pooled db access + config; built the app skeleton with router/NAV auto-discovery, `/health`, shared Jinja render helper and minimal templates; created every §12 contract stub with docstrings (27 markers); added style_lint, check_stubs, CI, PR template, CODEOWNERS, AGENTS/CLAUDE, DECISIONS, requirements register, task files and logs.
- Files: `Makefile`, `docker-compose.yml`, `.env.example`, `pyproject.toml`, `db/migrations/000_base_schema.sql`, `app/{config,db,migrate,main,templating,deps,permissions,audit,outbox,clock,money}.py`, `app/auth/**`, `app/domain/**`, `app/services/**`, `app/routes/auth.py`, `app/templates/**`, `scripts/{check_stubs,style_lint}.py`, `.github/**`, `docs/**`, `requirements.yaml`, `tests/conftest.py`, `tests/base/{test_health,test_schema,test_stubs}.py`.
- Contract changes: none — stubs created exactly as §12.
- Decisions: D-26 first admin/demo accounts; D-27 session cookie; D-28 reset tokens; D-29 root path (added to `docs/DECISIONS.md`).
- Tests: `make check` -> `43 passed, 1 warning in 4.91s` (ruff + style-lint clean, 27 stubs reported).
- Next: A-06..A-09.
- Needs from others: B: replace domain/service stubs; C: `app/static/ledger.css` for base.html; D: invariants and dashboard.

## 2026-10-31 12:38 IST — A — A-06..A-09 — DONE
- Did: clock backed by `clock_state` (real/simulated, month-end clamped advance, audited) and money helpers (Indian grouping, parse, half-up bps); full auth (signup with server-side password rules, CITEXT unique email, argon2id, signed session cookie, login/logout, forgot/reset via the outbox with single-use 30-minute tokens, Origin check); `require(permission)` and the §14 matrix; admin bootstrap from `ADMIN_EMAIL`/`ADMIN_PASSWORD`; `base.html` with nav filtered by role, SYSTEM DATE line and the footer timing; `scripts/gh_bootstrap.py` for labels, milestones, issues and branch protection.
- Files: `app/{clock,money,deps,permissions}.py`, `app/auth/**`, `app/routes/auth.py`, `app/templates/{base,auth/**,home,error}.html`, `app/templating.py`, `scripts/gh_bootstrap.py`, `tests/base/{test_clock,test_money,test_auth,test_permissions,test_time_ban}.py`, `tests/authz/test_route_matrix.py`, `tests/e2e/test_auth_flow.py`.
- Contract changes: none.
- Decisions: D-26..D-29 already recorded; no new ones.
- Tests: `make check` -> `44 passed, 1 warning in 6.27s` (ruff clean, style-lint clean, 27 stubs reported).
- Next: A-10 (staff users page, RBAC/IDOR tests).
- Needs from others: D to re-land invoices/payments/reports/invariants on base-0a (issue #6); C to merge C-01 so `ledger.css` exists; B to replace domain stubs.

## 2026-10-31 12:38 IST — A — merge captain — NOTE
- Did: D pushed 113d870 to main before base-0a existed; it could not import (`app.db.get_conn`, `app.auth.require`), had undefined names and a broken index migration, so I reverted the non-compiling files in 47881ef, kept the reusable SQL/Dockerfile/render.yaml/log, and opened issue #6 for D to rebase on `base-0a`.
- Files: `app/routes/{invoices,payments,reports}.py`, `app/services/{invoices,payments,reports,invariants}.py`, `scripts/{seed_scale,perf_check}.py`, `db/migrations/300_d_indexes.sql`, `app/templates/{invoices,payments,dashboard,overdue}/**`.
- Tests: `make check` -> `44 passed` after the revert.
