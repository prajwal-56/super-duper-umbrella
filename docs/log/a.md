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

## 2026-10-31 12:45 IST — A — A-09 follow-up — DONE
- Did: `gh_bootstrap.py` now closes task issues whose box is already ticked (PR #54, merged) and labels/milestones/issues/branch protection are live on GitHub; verified a fresh clone of `main` (`make setup && make migrate && make check`); smoke-tested uvicorn (`/health` 200, `/login` 200).
- Files: `scripts/gh_bootstrap.py`, `docs/log/a.md`.
- Contract changes: none.
- Decisions: none.
- Tests: fresh clone at a18318c -> `44 passed, 1 warning in 5.13s`; `make check` in the working tree -> `44 passed`.
- Next: A-10 (staff users page, RBAC matrix + IDOR tests).
- Needs from others: C: open the C-01 PR so `app/static/ledger.css` reaches main; B: PRs for B-01..B-04; D: rebase on `base-0a` (issue #6).

## 2026-10-31 13:04 IST — A — A-10 — DONE (users page + route × role matrix)
- Did: admin-only `/app/users` page (lists every account, creates staff) behind `require("staff:manage")`; `auth.service.create_staff` fixes the role server-side so the posted form cannot mint an admin; replaced the declaration-only route check with a full route × role walk that compares every response with §14 (403 only where the matrix refuses, never a 403 where it allows, DEMO_MODE restriction included); added the users-page tests (staff/customer 403, weak password and duplicate email 422, audit actor, nav visibility).
- Files: `app/routes/users.py`, `app/templates/users/index.html`, `app/auth/service.py`, `app/main.py`, `tests/authz/test_route_matrix.py`, `tests/authz/test_users_page.py`, `docs/DECISIONS.md`, `docs/tasks/a.md`.
- Contract changes: none.
- Decisions: D-30 (IDOR assertions move to A-11, where the first customer-facing routes exist), D-31 (the `base.html` class names are the layout contract; `ledger.css` must style them).
- Found: A-08 never populated `request.state.nav`, so the header nav rendered empty on every page; fixed in `app/main.py` and covered by the new nav-visibility test.
- Tests: `make check` -> `57 passed, 1 warning in 10.08s`.
- Next: A-11 portal (own subscriptions, own invoices, print view, profile) with the IDOR tests.
- Needs from others: C: C-01 does not implement the `base.html` class contract — issue filed, fix before merge; B/D: rebase their branches onto `main` (all five open PRs conflict and have no CI run).

## 2026-10-31 13:10 IST — A — A-13 — DONE
- Did: `/app/outbox` viewer behind `report:read`: newest 50 messages, kind filter that falls back to all kinds, each subject opens to the rendered body and its clickable link, SMTP column shows `not sent` when SMTP is off, and an empty state that says what will appear there.
- Files: `app/routes/outbox.py`, `app/templates/outbox/index.html`, `tests/base/test_outbox_page.py`, `docs/DECISIONS.md`, `docs/tasks/a.md`.
- Contract changes: none.
- Decisions: D-32 — the outbox renders `body_html` unescaped, so every `queue_email` caller must escape customer-supplied text when composing a body.
- Tests: `make check` -> `69 passed, 1 warning in 10.07s`.
- Next: A-12 `/app/clock` page (needs `lifecycle.run_daily` from B-07 to actually advance), A-11 portal once B-07 and D-02 land.
- Needs from others: B: rebase #2, #3, #4 on `main` (conflict is only `docs/log/b.md`); C: fix #5 (style lint: 3 inline `style=` attributes) and the class-name issue #57; D: rebase issue #6.

## 2026-10-31 13:22 IST — A — A-12 — DONE
- Did: `/app/clock` behind `clock:admin` (so DEMO_MODE only): current business date and mode, advance by days and months, jump to a date, reset to the real date. Every move goes through `app.clock`, which already calls `lifecycle.run_daily`, and writes a `clock.advance`/`clock.set_simulated`/`clock.reset` audit row with the admin as actor. Nav now hides DEMO_ONLY entries when demo mode is off, so the Clock link no longer 403s outside a demo.
- Files: `app/routes/clock.py`, `app/templates/clock/index.html`, `app/templating.py`, `tests/base/test_clock_page.py`, `docs/tasks/a.md`.
- Contract changes: none.
- Decisions: none.
- Tests: `make check` -> `78 passed, 1 warning in 12.92s`. The page tests record `lifecycle.run_daily` at the seam; the real daily job is B's tests plus the e2e path.
- Next: A-11 portal (blocked on B-07 and D-02), A-14 billing-run pages (blocked on B-06), A-15 seed, A-17 README.
- Needs from others: B: rebase #2, #3, #4; C: fix #5 and #57; D: nothing pushed yet, issue #6 is the whole money track.

## 2026-10-31 13:17 IST — A — A-14 — DONE (Tier 0)
- Did: `/app/billing-runs` behind `billing:run`: the form (as-of defaults to `clock.today()`, dry/live, "confirm invoices immediately"), the last 20 runs with considered/invoices/amount, and a result page with header counts, the run's integrity summary and a disposition table searchable by customer name or subscription id. Bad date or unknown mode returns 422 with the form; unknown run is a 404.
- Files: `app/routes/billing_runs.py`, `app/templates/billing_runs/{index,show}.html`, `tests/base/test_billing_runs_page.py`, `docs/tasks/a.md`.
- Contract changes: none — the page calls `billing.run_billing(as_of, mode, actor_id, auto_confirm)` exactly as §12 declares it.
- Decisions: none.
- Tests: `make check` -> `85 passed, 1 warning in 15.08s`. The live-run path goes through B's stub, so it is exercised by B-06's tests and the e2e, not here.
- Not built: the Tier 1 "confirm all drafts from this run" and "hammer it" buttons.
- Next: A-11 portal, A-15 seed, A-16 e2e, A-17 README.
- Needs from others: B: rebase #2, #3, #4, #60; C: #5 style lint + #57 class names; D: nothing pushed, issue #6.

## 2026-10-31 13:20 IST — A — A-11 — DONE (read-only)
- Did: the customer portal behind `portal:own`: `/portal` (own subscriptions, last ten invoices, outstanding), `/portal/subscriptions/{id}` (plan, dates, lines, invoices), `/portal/invoices`, `/portal/invoices/{id}` (print view with a `window.print()` button), `/portal/profile`. Every query goes through the new read model `app/services/portal.py` and filters on the customer id from the session, so another customer's id is a 404, not a 403.
- Files: `app/services/portal.py`, `app/routes/portal.py`, `app/templates/portal/*.html`, `tests/authz/test_portal_idor.py`, `docs/tasks/a.md`.
- Contract changes: none. `app/services/portal.py` is a new A-owned read model; it adds no §12 signature and duplicates no write path.
- Decisions: none.
- Tests: `make check` -> `91 passed, 1 warning in 15.53s`, including the two IDOR cases (another customer's subscription and invoice are 404) that D-30 moved here from A-10.
- Not built: pause/resume/close/renew buttons (need `lifecycle.allowed_actions`, B-07) and D's `invoice_print.html` partial (D-02); the portal renders its own print layout until then.
- Next: A-15 seed, A-16 e2e, A-17 README; merge captain at the 14:01 window.
- Needs from others: B: rebase #2, #3, #4, #60; C: #5 style lint + #57 class names; D: nothing pushed, issue #6.
