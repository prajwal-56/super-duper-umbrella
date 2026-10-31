# AGENTS.md — operating rules for every agent on this repo

Read `docs/BUILD_PLAN.md` fully at the start of every session. This file is
BUILD_PLAN §4 (verbatim) plus the pointers that make it usable.

## 4. AGENT OPERATING RULES

1. **Identity.** You are the agent of ONE handle (A, B, C or D). Your human's git identity is already configured. Never run `git config` to change it, never commit as a bot. Every commit must show your human as author.
2. **Session start (always, in this order):**
   `git fetch origin && git checkout main && git pull` → `make status` (prints the last entries of all four logs plus open issues) → read §17 for your handle and `docs/tasks/<handle>.md` → continue the first unchecked task, or the open PR you were on.
3. **Session end:** work committed and pushed on your branch, PR opened or updated, `docs/log/<handle>.md` appended (§6), task checkbox ticked.
4. **Truthfulness.** Never write "done", "working" or "passing" unless you ran the command in THIS session and saw it pass. Paste the final output line in the log. No fake data, no `TODO` bodies, no hardcoded demo data outside seed scripts. A function that is a placeholder must carry `# CONTRACT-STUB owner=<handle>`; `make check-stubs` must report zero stubs at freeze.
5. **Time.** The shell knows the real time; you do not. Use `date '+%Y-%m-%d %H:%M %Z'` for every log timestamp.
6. **Architecture rules (non-negotiable):**
   - Money is integer minor units (BIGINT). Never float. Display via `money.fmt()`.
   - Business time comes ONLY from `app.clock` (`today()`, `now()`). Banned in `app/` and `scripts/`: `date.today(`, `datetime.now(`, `datetime.utcnow(`, `time.time(`, and SQL `now()`/`CURRENT_DATE` in queries. Allowed only with a trailing `# real-time-ok` comment (security token expiry, request timing, log stamps). Migration `DEFAULT now()` on `created_at` is fine. A test enforces this.
   - Pure logic lives in `app/domain/` (no DB, no HTTP). DB logic lives in `app/services/`. Route handlers only authenticate, authorize, validate, call a service, render.
   - Raw SQL via psycopg with **parameterized queries only**. Never f-string values into SQL.
   - Every route declares a permission via `require("...")` (§14). The UI hiding a button is not security.
   - State changes go through ONE function per entity (§13.4). No ad-hoc `UPDATE ... SET status`.
   - Every state change and every money-affecting write calls `audit()` in the same transaction.
   - Billing, discount and payment tests run against REAL Postgres. No DB mocks there.
   - No JS framework, no inline styles, no new CSS outside the owner rules in §2 (§15 has the style law). Forms are plain POST → redirect (PRG).
   - No file over ~400 lines. No swallowed exceptions. Validation errors return the page with field messages and HTTP 422.
7. **Ambiguity.** Use `docs/DECISIONS.md` (§10). If not covered, choose the simplest defensible option, add a `D-xx` line to your log AND open a PR touching `docs/DECISIONS.md` via the lead (issue label `decision`), then continue. Do not wait.
8. **Stuck rule.** 15 minutes without progress → log `BLOCKED` with what you tried, open a GitHub issue (label `blocked`, mention the owner who can unblock), switch to your next task.
9. **LLM habits to actively resist:** building every screen shallowly; tests that cannot fail; weakening a test or invariant to make it pass (if an invariant fails, the engine is wrong); generic SaaS visuals; inventing features not in this plan; claiming work you did not run; editing files you do not own; huge PRs.

## Ownership

Path ownership is in BUILD_PLAN §2 and `.github/CODEOWNERS`. Only the owner
edits a path. Everyone else opens an issue labeled `request`. A tiny blocking
change in someone else's file may ride in your PR with a `TOUCHES <owner>: ...`
title and an @mention; the owner reviews first.

## Base modules owned by A (everyone may import, nobody else edits)

`app/main.py`, `app/config.py`, `app/db.py`, `app/migrate.py`, `app/clock.py`,
`app/money.py`, `app/audit.py`, `app/outbox.py`, `app/deps.py`,
`app/permissions.py`, `app/templating.py`, `app/auth/**`,
`app/templates/base.html` (plus `home.html` and `error.html`).

Template contract for `base.html`: pages extend it and fill `{% block content %}`.
`render(request, template, ...)` in `app/templating.py` injects `user`, `nav`,
`system_date`, `simulated` and `duration_ms`. Class names used by the layout:
`sheet`, `margin-rule`, `masthead`, `brand`, `nav` (`current`, `sep`), `whoami`,
`identity`, `system-date` (`simulated`), `content`, `folio`, `section`,
`section-label`, `field`, `button` (`primary`, `destructive`), `notice`, `error`,
`errors`, `hint`, `small`, `link-button`, `form`, `logout-form`. C styles these
in `app/static/ledger.css`.
