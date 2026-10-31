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
