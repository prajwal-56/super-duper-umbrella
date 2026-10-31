# BRIGHTLOOP BILLING — BUILD PLAN v2 (4 people, ~5.5 hours)

## HUMAN FILL-IN (A fills this in, then commits)
- START_TIME (T0): Right now          FREEZE_TIME (T0 + 4:30): __:__          SUBMIT_TIME (T0 + 5:30): __:__
- HANDLES (GitHub usernames): A=prajwal-56 (lead)  B=ohaswin (engine)  C= KStupid (catalog/UI)  D=shreeram-tech(money/reports)
- PRODUCT_NAME: Brightloop Ledger        DEPLOY_TARGET: Render (default)
- TOTAL_HOURS_LEFT: 5.5   (if 5.0: freeze at T+4:00, G2 at T+2:15, G3 at T+3:20, drop every Tier 1 item)

---

## 1. READ FIRST (every agent, every session)

**Mission:** a subscription billing system for "Brightloop Software" that never double-bills, never skips a period, explains every number, and stays fast with thousands of subscriptions. Built by 4 humans, each with their own coding agent, working in parallel on one GitHub repo.

**Win thesis.** Judges will see the same seven scenes from many teams. We win by being the build that cannot be broken live and can justify every figure:
1. **Simulated clock.** The demo walks a literal billing month in minutes. All time goes through one `clock` module.
2. **Billing-run ledger.** Every subscription in a run gets a recorded disposition and reason. "Skipped" cannot hide.
3. **Integrity page.** Independent SQL checks that must stay green (no duplicate periods, no missing periods, totals reconcile, discount counters consistent, dashboard equals raw data).
4. **Explain every number.** Each invoice line stores a calculation trace, shown as a waterfall.
5. **Perf receipts.** 8k+ seeded subscriptions, a "set in N ms" footer on every page, a published p95 table.
6. **A rare, deliberate look** (§15) instead of the default LLM SaaS look.

**Self-awareness note (this plan was drafted by an LLM that gives similar advice to many teams).** Assume most serious teams also have RBAC, state machines, an idempotency constraint, an audit log, seeded data and KPI cards; those are required for us, not distinguishing. Our edge is (a) proof, not claims, (b) a demo that walks time, (c) a coherent aesthetic, (d) a disciplined 4-person workflow that ships a finished, deployed product. If the differentiators don't land with the judges, finished and correct Tier 0 is the fallback. Never trade Tier 0 for a differentiator.

---

## 2. TEAM, TRACKS, OWNERSHIP

| Handle | Track | Summary |
|---|---|---|
| A (lead) | Base + access + integration | scaffold, schema, auth, RBAC, portal, clock, outbox, billing-run pages, seed demo, README, merge captain |
| B | Engine | pure domain logic, billing run, discounts, lifecycle, concurrency tests |
| C | Catalog + subscriptions + UI system | design system CSS and macros, catalog, customers, templates, subscription builder and pages, discount rules admin |
| D | Money + reporting + ops | invoices, payments, dashboard, integrity, indexes, scale seed, perf, deploy |

**Path ownership (only the owner edits these; everyone else requests changes via a GitHub issue labeled `request`):**
- **A:** `Makefile`, `docker-compose.yml`, `.github/**`, `AGENTS.md`, `CLAUDE.md`, `README.md`, `requirements.yaml`, `docs/BUILD_PLAN.md`, `docs/DECISIONS.md`, `docs/JUDGE_QA.md`, `app/main.py`, `app/config.py`, `app/db.py`, `app/migrate.py`, `app/clock.py`, `app/money.py`, `app/audit.py`, `app/outbox.py`, `app/deps.py`, `app/permissions.py`, `app/auth/**`, `app/routes/{auth,users,portal,clock,outbox,demo,billing_runs}.py`, `app/templates/base.html`, `app/templates/{auth,portal,users,clock,outbox,billing_runs}/**`, `db/migrations/0xx_*`, `scripts/{seed_demo,gh_bootstrap,style_lint,check_stubs}.py`, `tests/{conftest,factories}.py`, `tests/{authz,e2e,base}/**`
- **B:** `app/domain/**`, `app/services/{billing,lifecycle,discount_engine,chaos}.py`, `app/jobs/**`, `app/routes/internal.py`, `db/migrations/1xx_*`, `tests/engine/**`
- **C:** `app/static/ledger.css`, `app/templates/_ui.html`, `app/services/{catalog,subscription_builder,customers}.py`, `app/routes/{catalog,customers,subscriptions,discounts,styleguide}.py`, `app/templates/{catalog,customers,subscriptions,discounts}/**`, `db/migrations/2xx_*`, `tests/catalog/**`
- **D:** `app/services/{invoices,payments,reports,invariants}.py`, `app/routes/{invoices,payments,dashboard,integrity}.py`, `app/templates/{invoices,payments,dashboard,integrity}/**`, `db/queries/**`, `db/migrations/3xx_*`, `scripts/{seed_scale,perf_check}.py`, `Dockerfile`, `render.yaml`, `docs/PERF.md`, `tests/money/**`
- Each person also owns `docs/log/<handle>.md` and `docs/tasks/<handle>.md`.
- Extra CSS from non-C owners: put it in `app/static/mod_<handle>.css` (auto-loaded by `base.html`). Never inline styles.
- `requirements.txt`: anyone may append one dependency line (alphabetical) in a tiny PR announced in their log; nothing else changes in that file.
- **Tiny blocking change in someone else's file:** make it in your PR, title it `TOUCHES <owner>: ...`, @mention the owner. The owner reviews first.
- **Idle?** Self-assign an open issue labeled `unassigned`. Never start inventing features.

---

## 3. TIMELINE (T0 = START_TIME; clock times in the HUMAN FILL-IN)

| When | Gate / tag | What must be true |
|---|---|---|
| T+0:00–0:25 | A builds base-0a. B, C, D do no-dependency prep (see §17) | |
| T+0:25 | **G0 `base-0a`** | schema, skeleton app, contract stubs, CI, Makefile pushed. B/C/D clone and start feature work |
| T+0:25–0:55 | A builds auth, clock, layout, GitHub bootstrap | |
| T+0:55 | **G1 `base-v1`** | login works, `main` is protected, issues exist, `make check` green on a clean clone |
| T+1:00, 2:00, 3:00, 4:00 | **Sync windows** (5 min, whole team) | merge every green PR, everyone pulls `main`, A posts `make status` output to team chat |
| T+2:30 | **G2 `g2-slice`** | one scripted path works on `main`: signup → catalog → subscription → activate → invoice → confirm → payment → dashboard |
| T+3:45 | **G3 `g3-complete`** | all Tier 0 features merged, e2e and RBAC tests green on `main` |
| T+4:15 | **G4 `g4-hardened`** | scale seed loaded, perf under budget, integrity all green, style pass done |
| T+4:30 | **FREEZE `freeze`** | no features after this. Bug fixes only, PR label `freeze-fix`, A approves |
| T+4:30–5:15 | Rehearse the demo 3×, record backup video, fresh-clone test, final README check | |
| T+5:30 | **`submission`** | submitted |

Rule: if a gate is missed by 15 minutes, the lead cuts scope per §20 immediately. Do not extend deadlines.

---

## 4. AGENT OPERATING RULES (A copies this section into `AGENTS.md` and `CLAUDE.md`)

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

---

## 5. GIT AND GITHUB PROTOCOL (everyone, no exceptions)

**Before G1:** only A pushes to `main`, directly, in small commits. After `base-v1`, `main` is protected: PR required, CI must pass, no force-push, no direct push, 0 required approvals (authors self-merge when green).

**Branches:** `<handle>/<task-id>-<slug>`, e.g. `b/B-05-bill-subscription`. One task, one branch, one PR.

**Commit cadence:** commit every logical unit that passes its tests, at least every ~20 minutes or ~100 changed lines; `git push` after every commit (backup and visibility). Commit as yourself.

**Conventional Commits:** `feat(billing): derive expected periods anchor-relative`, `test(billing): concurrent runs create no duplicates`, `fix(discounts): claim counter in invoice txn`, `perf(reports): partial index for overdue`, `docs(log): B-05 done`. Body says what and why. Footer `Req: R-BILL-03` when relevant.

**Pull request rules:**
- Open a PR within 45 minutes of starting a task; keep PRs under ~300 changed lines where possible.
- Before opening or merging: `git fetch origin && git rebase origin/main` (or merge `main` in), then `make check`. Paste the last line of `make check` in the PR body.
- Title in Conventional Commit style. Body from the template: Task ID, `Closes #<issue>`, Req IDs, what changed, how tested, contract changes (none / list), `TOUCHES` notes.
- The same PR includes your `docs/log/<handle>.md` entry and ticks your `docs/tasks/<handle>.md` box.
- Merge with **"Create a merge commit"** (never squash: individual commits are our contribution record). Delete the branch after merging.
- Never `git push --force` to shared branches. Never rewrite pushed history. Rebase only your own unmerged feature branch.

**Conflict-avoidance structure (already designed in, keep it):**
- Routers auto-register: every `app/routes/*.py` exposes `router` and optionally `NAV = [(label, path, permission)]`. Nobody edits `main.py` or a shared nav file.
- Migrations are plain SQL files `db/migrations/NNN_<handle>_<slug>.sql`. Ranges: A 000–099, B 100–199, C 200–299, D 300–399. The runner applies every unapplied file in filename order (not just files newer than the last one), and records them in `schema_migrations`. Never edit an applied migration; add a new one. All base tables exist from `000_base_schema.sql`, so most people never need a migration.
- Per-person log files and task files (no shared appends).
- Contract changes (any signature in §12): open an issue labeled `contract-change`, mention every dependent owner, and log it. Do not change a signature silently.

**Tags (A only):** `base-0a`, `base-v1`, `g2-slice`, `g3-complete`, `g4-hardened`, `freeze`, `submission`.

**Contribution record:** every member must have at least 8 merged commits across at least 3 merged PRs by freeze. A checks `git shortlog -sn` at G3 and reassigns tasks if someone is blocked.

---

## 6. SHARED AGENT LOG

File: `docs/log/<handle>.md`. Append-only, newest at the bottom, written by your agent, committed in the same PR as the work. This is how four agents stay aligned without talking.

Entry format:

```
## 2026-10-31 15:42 IST — B — B-05 — DONE | WIP | BLOCKED
- Did: <1-3 lines>
- Files: <paths>
- Contract changes: none | <old signature -> new signature, issue #>
- Decisions: none | D-xx <one line>
- Tests: <command> -> <last output line>
- Next: <next task id>
- Needs from others: none | <owner>: <what> (issue #)
```

`make status` prints the last 3 entries of every log plus `gh issue list --state open` (falls back to logs only if `gh` is unavailable). Every agent reads it at session start. Read other people's logs before touching anything they might depend on.

---

## 7. STACK AND REPO LAYOUT

- Python 3.12, FastAPI, Uvicorn, Jinja2 (server-rendered), psycopg 3 (+ pool), Pydantic v2, argon2-cffi, itsdangerous (signed session cookie), python-multipart, httpx, pytest, ruff. PostgreSQL 16. **No JS framework, no Redis, no queue, no ORM, no payment gateway.**
- Windows teammates: use WSL2, or run the underlying commands in the `Makefile` directly.

```
/
├─ AGENTS.md  CLAUDE.md  README.md  requirements.txt  requirements.yaml  Makefile
├─ docker-compose.yml  Dockerfile  render.yaml  .env.example
├─ .github/  workflows/ci.yml  pull_request_template.md  CODEOWNERS
├─ docs/  BUILD_PLAN.md DECISIONS.md JUDGE_QA.md PERF.md  log/{a,b,c,d}.md  tasks/{a,b,c,d}.md
├─ db/  migrations/NNN_<handle>_<slug>.sql   queries/*.sql
├─ scripts/  seed_demo.py seed_scale.py perf_check.py style_lint.py check_stubs.py gh_bootstrap.py
├─ app/
│  ├─ main.py config.py db.py migrate.py clock.py money.py audit.py outbox.py deps.py permissions.py
│  ├─ auth/  domain/  services/  routes/  jobs/
│  ├─ templates/  base.html _ui.html  <area>/...
│  └─ static/  ledger.css  mod_<handle>.css
└─ tests/  conftest.py factories.py  base/ authz/ e2e/ engine/ catalog/ money/
```

**Makefile targets (A builds; README documents these exact names):** `setup`, `db-up`, `db-down`, `migrate`, `seed`, `seed-scale`, `dev` (uvicorn --reload :8000), `test`, `lint` (ruff), `style-lint`, `check-stubs`, `check` (= lint + style-lint + test; prints stub report), `invariants`, `perf`, `reset-demo`, `status`.

**Config (env):** `DATABASE_URL`, `TEST_DATABASE_URL`, `SECRET_KEY`, `APP_BASE_URL`, `DEMO_MODE` (true/false), `SEED_ON_BOOT` (true/false, seeds only if no users exist), `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `CRON_TOKEN`, `SMTP_*` (optional), `CURRENCY_CODE=INR`, `BUSINESS_TZ=Asia/Kolkata`.

---

## 8. HOW A MONTH WORKS (the model every agent must share)

Customer signs up → admin/staff builds catalog (products, variants, plans, taxes, payment terms, templates) → staff creates a subscription (from a template or manually) → Draft → Quotation (sent, valid N days) → Confirmed → Active (first period invoice is created) → on billing day, the billing run bills every due period of every active subscription exactly once → invoices are Draft; staff Confirm/Send/Print them → payments are recorded against invoices (partials allowed) → invoice becomes Paid when fully paid → finance lead sees active subscriptions, revenue, outstanding, overdue, with filters. The simulated clock lets us jump through all of this in a demo.

---

## 9. REQUIREMENTS REGISTER (A copies into `requirements.yaml`; tag tests with the ID in the test name or a comment)

AUTH / ACCESS
- R-AUTH-01 Signup with email + password creates a customer account (and its customer record).
- R-AUTH-02 One account per email (case-insensitive).
- R-AUTH-03 Password: MORE than 8 characters (so ≥ 9), ≥ 1 uppercase, ≥ 1 lowercase, ≥ 1 special character. Server-side. 8 chars must fail.
- R-AUTH-04 Forgot password sends a reset link to the registered email (single-use, expiring, identical response whether or not the email exists).
- R-RBAC-01 Roles admin, staff, customer, with the matrix in §14.
- R-RBAC-02 Only admin can add staff.
- R-RBAC-03 Customers see only their own subscriptions and invoices, including by direct URL/ID.
- R-RBAC-04 Only admin can create discount rules.

CATALOG
- R-PROD-01 Product: name, type, sales price, cost price, notes.
- R-PROD-02 Variants (e.g. brand) with extra price (Odoo = +560.00) flowing to subscription lines and invoices.
- R-PLAN-01 Plan: price, billing period (daily/weekly/monthly/yearly), minimum quantity, availability dates.
- R-PLAN-02 Per-plan flags (auto-close, allow early close, allow pause, allow renew) enforced.
- R-TPL-01 Quotation template: plan + product lines + validity days.
- R-TAX-01 Admin-defined tax rules applied automatically.
- R-PT-01 Payment terms.

SUBSCRIPTIONS
- R-SUB-01 Number, customer, plan, start date, expiry date, payment terms.
- R-SUB-02 Lines: product, quantity, unit price, taxes, amount.
- R-SUB-03 Create from quotation template.
- R-SUB-04 Lifecycle Draft → Quotation → Confirmed → Active → Closed, enforced server-side, visible to the team.
- R-SUB-05 Quote validity expires after N days.
- R-SUB-06 Pause/resume, early close, renew (per plan flags); auto-close.

BILLING
- R-BILL-01 Invoice generated from subscription with customer details, lines, taxes, totals filled in.
- R-BILL-02 One action bills all due subscriptions.
- R-BILL-03 Never billed twice (idempotent, crash-safe, concurrency-safe).
- R-BILL-04 Never skipped (catch-up; every candidate accounted for in the run).
- R-BILL-05 Taxes auto-calculated from admin rules.
- R-BILL-06 Invoice actions: confirm, cancel, send, print.
- R-BILL-07 Invoice lifecycle Draft → Confirmed → Paid.

DISCOUNTS
- R-DISC-01 Fixed or percentage; min purchase or min quantity; start/end dates; usage limit.
- R-DISC-02 Applies to specific products or whole subscriptions.
- R-DISC-03 Appears on the next invoice automatically.
- R-DISC-04 Stops on expiry or exhaustion (race-safe).

PAYMENTS / REPORTING / PORTAL
- R-PAY-01 Record method, amount, date, note against an invoice.
- R-PAY-02 Paid vs outstanding visible at any moment.
- R-PAY-03 Overdue invoices identifiable and chaseable.
- R-RPT-01 One place for active subscriptions, revenue, payments, overdue invoices.
- R-RPT-02 Filters and a summary view.
- R-RPT-03 Every page responds in under 2 s with thousands of subscriptions.
- R-PORT-01 Customer portal to view and manage own subscriptions and view invoices.

OURS
- X-CLK-01 Simulated clock (admin, DEMO_MODE only).
- X-RUN-01 Billing-run dispositions and dry-run through the same code path.
- X-INV-01 Integrity page with independent SQL checks.
- X-EXP-01 Calculation trace on invoice lines, shown in the UI.
- X-PERF-01 Scale seed, perf report, server-time footer.
- X-OUT-01 Email outbox viewer.

---

## 10. DECISIONS (A copies into `docs/DECISIONS.md`; add more as needed)

- **D-01 Money:** integer minor units, single currency (INR default). "560" means 560.00. Tax rates in basis points (18% = 1800). Cells show no currency symbol; column headers say "(INR)". Display uses Indian digit grouping (1,23,456.00). Negative amounts shown in parentheses.
- **D-02 Rounding:** half-up at the LINE level; invoice totals are exact sums of line values. Subscription-scope discounts are allocated across lines by largest remainder so the sum is exact.
- **D-03 Tax:** each tax rule is inclusive or exclusive; computed AFTER discounts; rate and inclusive flag are snapshotted on lines. Exclusive: `tax = round(net * rate / 10000)`, `total = net + tax`. Inclusive: `net = round(gross * 10000 / (10000 + rate))`, `tax = gross - net`, `total = gross`.
- **D-04 Price resolution (ASSUMPTION, confirm with organizers if possible):** line unit price = `product_plan_prices` override if present else `product.sales_price`, plus the variant's `extra_price`. If `plan.price_minor > 0`, each billing period also gets one "Plan fee" line (qty 1, plan's tax = none). Subscription lines SNAPSHOT price and tax at creation; later catalog edits never change existing subscriptions.
- **D-05 Billing is in advance, anchor-relative:** period k = `[start + k*step, start + (k+1)*step - 1 day]` where step = `interval_count` × unit. Month/year math is computed from the anchor (`start + k months`, clamped to month end), never iteratively, so Jan 31 → Feb 28 → Mar 31 has no drift. `expiry_date` is the last day of coverage (inclusive); periods are included while `period_start <= expiry_date`.
- **D-06 Dates:** `issue_date` = clock today at invoice creation; `due_date = issue_date + payment_term.due_days`.
- **D-07 Overdue** = invoice is `confirmed` AND outstanding > 0 AND `due_date < clock.today()`. Derived, never stored.
- **D-08 Pause:** periods that START inside a pause window are not billed and not back-filled (disposition `skipped_paused`). Pause is a flag with history; status stays Active (UI shows "Active · Paused"). Expiry does not move.
- **D-09 Subscription status** has exactly the five spec states.
- **D-10 Auto-close:** if `plan.auto_close`, an Active subscription closes when `as_of > min(expiry_date, plan.available_to)` with `closed_on` = that date. Otherwise it stays Active after expiry (no billing past expiry) and shows in an "expired, needs closing" filter.
- **D-11 Discounts:** evaluated per invoice at generation. Eligible if `active`, `as_of` within `[starts_on, ends_on]`, min purchase/quantity met within scope, usage remaining, and (`auto_apply` OR attached via `subscription_discounts`). Stacking: at most one best discount per line (product scope) plus at most one best discount at subscription scope applied to the post-line-discount subtotal. Best = largest saving; ties by earliest `ends_on`. One redemption = one invoice that applied the rule. Cancelling an invoice voids its redemptions and releases usage.
- **D-12 Payments:** partial payments allowed; overpayment rejected (422); only against `confirmed` invoices; invoice becomes `paid` when `amount_paid == total`; an invoice with payments cannot be cancelled; no reversals.
- **D-13 Invoice numbers:** assigned at confirmation from a sequence, format `INV-<year>-<6 digits>`; gaps are allowed and documented. Drafts show "DRAFT".
- **D-14 Immutability (Tier 1):** a DB trigger blocks changes to financial columns of non-draft invoices.
- **D-15 Cancelled periods:** a cancelled invoice voids its period. The billing run does NOT silently re-bill it: disposition `skipped_period_voided` with reason "cancelled invoice, re-issue manually". (Re-issue UI is Tier 2.)
- **D-16 Quote validity:** starts when the quote is sent: `quote_valid_until = sent date + validity_days`. Confirming after that returns 409.
- **D-17 Min quantity** from the plan applies to each subscription line.
- **D-18 Plan availability:** a plan can be chosen for a new subscription only if today is within `[available_from, available_to]` (nulls = open).
- **D-19 Early close** stops future periods; no refund or proration (documented). Periods that started before the close date still get billed.
- **D-20 Timezone:** one business timezone for dates; timestamps stored UTC.
- **D-21 Send** = write to `emails_outbox` always (SMTP optional). Only `confirmed` invoices can be sent.
- **D-22 Dry-run** runs the exact live code path, rolls back each subscription's transaction, and records the would-be result.
- **D-23 MRR:** pre-tax recurring amount of Active, non-paused subscriptions, normalized to monthly (day × 365/12, week × 52/12, month × 1, year ÷ 12), ignoring discounts.
- **D-24 Renew:** extends `expiry_date` by the original term length when `plan.allow_renew`; allowed on Active; no new subscription row.
- **D-25 No cursor cache:** billing derives expected periods from facts every run; there is no `next_period_start` column.

---

## 11. SCHEMA (A writes `db/migrations/000_base_schema.sql` from this, verbatim in intent; add FK indexes)

```sql
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE customers (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT, address TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY, email CITEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','staff','customer')),
  customer_id BIGINT REFERENCES customers(id), is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE password_reset_tokens (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ);

CREATE TABLE taxes (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, rate_bps INT NOT NULL CHECK (rate_bps >= 0),
  inclusive BOOLEAN NOT NULL DEFAULT false, active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE payment_terms (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, due_days INT NOT NULL CHECK (due_days >= 0));

CREATE TABLE products (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
  sales_price_minor BIGINT NOT NULL CHECK (sales_price_minor >= 0),
  cost_price_minor BIGINT NOT NULL DEFAULT 0 CHECK (cost_price_minor >= 0),
  notes TEXT, tax_id BIGINT REFERENCES taxes(id), active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE product_variants (
  id BIGSERIAL PRIMARY KEY, product_id BIGINT NOT NULL REFERENCES products(id),
  attribute TEXT NOT NULL, value TEXT NOT NULL, extra_price_minor BIGINT NOT NULL DEFAULT 0,
  UNIQUE (product_id, attribute, value));

CREATE TABLE plans (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL,
  price_minor BIGINT NOT NULL DEFAULT 0 CHECK (price_minor >= 0),
  billing_interval TEXT NOT NULL CHECK (billing_interval IN ('day','week','month','year')),
  interval_count INT NOT NULL DEFAULT 1 CHECK (interval_count >= 1),
  min_quantity INT NOT NULL DEFAULT 1 CHECK (min_quantity >= 1),
  available_from DATE, available_to DATE,
  auto_close BOOLEAN NOT NULL DEFAULT false, allow_early_close BOOLEAN NOT NULL DEFAULT true,
  allow_pause BOOLEAN NOT NULL DEFAULT true, allow_renew BOOLEAN NOT NULL DEFAULT true,
  active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE product_plan_prices (
  product_id BIGINT REFERENCES products(id), plan_id BIGINT REFERENCES plans(id),
  price_minor BIGINT NOT NULL CHECK (price_minor >= 0), PRIMARY KEY (product_id, plan_id));

CREATE TABLE quotation_templates (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, plan_id BIGINT NOT NULL REFERENCES plans(id),
  validity_days INT NOT NULL CHECK (validity_days >= 1),
  payment_term_id BIGINT REFERENCES payment_terms(id));

CREATE TABLE quotation_template_lines (
  id BIGSERIAL PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES quotation_templates(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL CHECK (quantity >= 1));

CREATE SEQUENCE subscription_number_seq;
CREATE SEQUENCE invoice_number_seq;

CREATE TABLE subscriptions (
  id BIGSERIAL PRIMARY KEY,
  number TEXT NOT NULL UNIQUE DEFAULT ('SUB-' || lpad(nextval('subscription_number_seq')::text, 6, '0')),
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  plan_id BIGINT NOT NULL REFERENCES plans(id),
  template_id BIGINT REFERENCES quotation_templates(id),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','quotation','confirmed','active','closed')),
  start_date DATE NOT NULL, expiry_date DATE NOT NULL CHECK (expiry_date >= start_date),
  payment_term_id BIGINT NOT NULL REFERENCES payment_terms(id),
  quote_sent_on DATE, quote_valid_until DATE,
  is_paused BOOLEAN NOT NULL DEFAULT false, closed_on DATE, close_reason TEXT,
  billing_complete BOOLEAN NOT NULL DEFAULT false,
  version INT NOT NULL DEFAULT 1,
  created_by BIGINT REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE subscription_lines (
  id BIGSERIAL PRIMARY KEY,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL CHECK (quantity >= 1),
  unit_price_minor BIGINT NOT NULL CHECK (unit_price_minor >= 0),
  tax_id BIGINT REFERENCES taxes(id),
  tax_rate_bps INT NOT NULL DEFAULT 0, tax_inclusive BOOLEAN NOT NULL DEFAULT false);

CREATE TABLE subscription_pauses (
  id BIGSERIAL PRIMARY KEY, subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  paused_on DATE NOT NULL, resumed_on DATE);

CREATE TABLE discounts (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('fixed','percent')),
  value BIGINT NOT NULL CHECK (value > 0),           -- minor units if fixed, basis points if percent
  min_purchase_minor BIGINT, min_quantity INT,
  starts_on DATE NOT NULL, ends_on DATE NOT NULL CHECK (ends_on >= starts_on),
  usage_limit INT CHECK (usage_limit IS NULL OR usage_limit > 0),
  usage_count INT NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
  scope TEXT NOT NULL CHECK (scope IN ('product','subscription')),
  product_id BIGINT REFERENCES products(id),
  auto_apply BOOLEAN NOT NULL DEFAULT true, active BOOLEAN NOT NULL DEFAULT true,
  created_by BIGINT REFERENCES users(id),
  CHECK (kind <> 'percent' OR value <= 10000),
  CHECK (scope <> 'product' OR product_id IS NOT NULL),
  CHECK (usage_limit IS NULL OR usage_count <= usage_limit));

CREATE TABLE subscription_discounts (
  subscription_id BIGINT REFERENCES subscriptions(id), discount_id BIGINT REFERENCES discounts(id),
  PRIMARY KEY (subscription_id, discount_id));

CREATE TABLE billing_runs (
  id BIGSERIAL PRIMARY KEY, mode TEXT NOT NULL CHECK (mode IN ('dry','live')), as_of DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
  started_by BIGINT REFERENCES users(id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ,
  considered INT NOT NULL DEFAULT 0, invoices_created INT NOT NULL DEFAULT 0,
  amount_minor BIGINT NOT NULL DEFAULT 0, blocked_duplicates INT NOT NULL DEFAULT 0,
  integrity_summary JSONB);

CREATE TABLE invoices (
  id BIGSERIAL PRIMARY KEY, number TEXT UNIQUE,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  period_start DATE NOT NULL, period_end DATE NOT NULL,
  issue_date DATE NOT NULL, due_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','confirmed','paid','cancelled')),
  subtotal_minor BIGINT NOT NULL, discount_minor BIGINT NOT NULL DEFAULT 0,
  tax_minor BIGINT NOT NULL, total_minor BIGINT NOT NULL,
  amount_paid_minor BIGINT NOT NULL DEFAULT 0,
  billing_run_id BIGINT REFERENCES billing_runs(id), sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (amount_paid_minor >= 0 AND amount_paid_minor <= total_minor));
-- THE KEY CONSTRAINT (idempotency):
CREATE UNIQUE INDEX uq_invoice_period ON invoices (subscription_id, period_start) WHERE status <> 'cancelled';

CREATE TABLE invoice_lines (
  id BIGSERIAL PRIMARY KEY,
  invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL, product_id BIGINT REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL, unit_price_minor BIGINT NOT NULL,
  line_subtotal_minor BIGINT NOT NULL,            -- quantity * unit price, as entered
  discount_minor BIGINT NOT NULL DEFAULT 0,       -- total discount on this line (line + allocated)
  tax_rate_bps INT NOT NULL DEFAULT 0, tax_inclusive BOOLEAN NOT NULL DEFAULT false,
  tax_minor BIGINT NOT NULL DEFAULT 0,
  total_minor BIGINT NOT NULL,                    -- subtotal - discount (+ tax if exclusive)
  calc_trace JSONB NOT NULL DEFAULT '[]');

CREATE TABLE discount_redemptions (
  id BIGSERIAL PRIMARY KEY, discount_id BIGINT NOT NULL REFERENCES discounts(id),
  invoice_id BIGINT NOT NULL REFERENCES invoices(id), amount_minor BIGINT NOT NULL,
  voided_at TIMESTAMPTZ, UNIQUE (discount_id, invoice_id));

CREATE TABLE payments (
  id BIGSERIAL PRIMARY KEY, invoice_id BIGINT NOT NULL REFERENCES invoices(id),
  method TEXT NOT NULL CHECK (method IN ('cash','bank_transfer','card','upi','cheque','other')),
  amount_minor BIGINT NOT NULL CHECK (amount_minor > 0), paid_on DATE NOT NULL, note TEXT,
  recorded_by BIGINT REFERENCES users(id), idempotency_key TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE billing_run_items (
  id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL REFERENCES billing_runs(id) ON DELETE CASCADE,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  disposition TEXT NOT NULL CHECK (disposition IN
    ('billed','up_to_date','skipped_paused','skipped_period_voided','deferred_locked','failed')),
  periods_billed INT NOT NULL DEFAULT 0, invoice_ids BIGINT[] NOT NULL DEFAULT '{}',
  reason TEXT, error TEXT);
-- one item per candidate subscription; dominant disposition priority:
-- billed > failed > deferred_locked > skipped_period_voided > skipped_paused > up_to_date

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, at TIMESTAMPTZ NOT NULL DEFAULT now(), actor_id BIGINT,
  action TEXT NOT NULL, entity TEXT NOT NULL, entity_id BIGINT NOT NULL,
  before JSONB, after JSONB);
CREATE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION '% is append-only', TG_TABLE_NAME; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

CREATE TABLE emails_outbox (
  id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, to_email TEXT NOT NULL, subject TEXT NOT NULL,
  body_html TEXT NOT NULL, link TEXT, smtp_status TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE clock_state (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  mode TEXT NOT NULL DEFAULT 'real' CHECK (mode IN ('real','simulated')),
  simulated_today DATE, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
INSERT INTO clock_state (id) VALUES (1);

CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());
```

D adds performance indexes in `300_d_indexes.sql` (partial index on confirmed invoices by due date; invoices by customer/issue date/subscription; payments by invoice and paid date; subscriptions by status and customer; trigram GIN on customer name, subscription number, invoice number).

---

## 12. CONTRACTS BETWEEN TRACKS (A creates stubs for all of these in base-0a; owners replace them)

A stub looks like: `def f(...): raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B`. Docstring states exact behavior. Signatures are fixed unless changed through a `contract-change` issue.

```
# A: app/db.py
conn() -> contextmanager yielding psycopg.Connection (dict rows, autocommit off, commit on clean exit, rollback on error)
# A: app/clock.py
today() -> date ; now() -> datetime(aware, UTC) ; get_state() -> dict
advance(days=0, months=0, actor_id=None) -> date ; set_simulated(d: date, actor_id) -> None ; reset(actor_id) -> None
# A: app/money.py
fmt(minor: int) -> str   # '1,23,456.00' ; parse(text: str) -> int ; round_half_up_bps(amount: int, bps: int) -> int
# A: app/audit.py
audit(conn, actor_id, action: str, entity: str, entity_id: int, before=None, after=None) -> None
# A: app/outbox.py
queue_email(conn, kind: str, to_email: str, subject: str, body_html: str, link: str | None = None) -> int
# A: app/deps.py
require(permission: str) -> dependency returning User(id, email, role, customer_id)

# B: app/domain (pure, no DB)
periods.expected_periods(start, expiry, unit, count, as_of, closed_on, pauses: list[(date, date|None)], cap=36) -> list[Period(index, start, end, paused: bool)]
pricing.price_invoice(lines: list[LineInput], discounts: list[DiscountInput], as_of) -> PricedInvoice   # includes calc_trace per line
discounts.select(lines, candidates, as_of) -> list[Applied]
state_machines.SUBSCRIPTION_TRANSITIONS ; state_machines.can_transition(entity, from_status, to_status) -> bool
# B: app/services/lifecycle.py
transition(conn, subscription_id, to_status, actor_id, expected_version=None) -> dict
pause(conn, sub_id, actor_id) ; resume(conn, sub_id, actor_id) ; close(conn, sub_id, actor_id, reason) ; renew(conn, sub_id, actor_id)
allowed_actions(conn, subscription_id, role) -> list[str]     # drives UI buttons and the portal
run_daily(as_of, actor_id=None) -> dict                       # auto-activate, auto-close; called on clock change and by the daily job
# B: app/services/billing.py
bill_subscription(conn, subscription_id, as_of, actor_id, run_id=None, auto_confirm=False) -> list[int]   # invoice ids created
run_billing(as_of, mode: 'dry'|'live', actor_id, auto_confirm=False, subscription_ids=None) -> int       # billing_runs.id
# B (Tier 1): app/services/chaos.py
hammer(workers: int, rounds: int, actor_id) -> dict

# C: app/services/catalog.py
resolve_unit_price(conn, product_id, variant_id, plan_id) -> int
build_line_snapshot(conn, product_id, variant_id, quantity, plan_id) -> dict   # unit price, tax id/rate/inclusive
# C: app/services/subscription_builder.py
create_draft(conn, customer_id, plan_id, start_date, expiry_date, payment_term_id, lines, template_id=None, actor_id=None) -> int
create_from_template(conn, template_id, customer_id, start_date, actor_id) -> int

# D: app/services/invoices.py
confirm(conn, invoice_id, actor_id) ; confirm_many(conn, invoice_ids, actor_id) -> int ; cancel(conn, invoice_id, actor_id, reason)
send(conn, invoice_id, actor_id) ; get_for_customer(conn, invoice_id, customer_id) -> dict | None
# D: app/services/payments.py
record(conn, invoice_id, method, amount_minor, paid_on, note, actor_id, idempotency_key=None) -> int
# D: app/services/reports.py
dashboard(conn, filters: dict) -> dict ; overdue(conn, filters, page, page_size) -> dict
# D: app/services/invariants.py
run_all(conn) -> list[InvariantResult(id, name, ok, violations, sample_rows)]
```

---

## 13. ENGINE SPECS (B implements; A, C and D rely on them)

### 13.1 Clock (A)
`clock_state` table: `real` returns the actual date; `simulated` returns `simulated_today`. `advance()` and `set_simulated()` write audit rows and (when DEMO_MODE) call `lifecycle.run_daily(new_date)`. The UI shows a persistent top-bar line: `SYSTEM DATE 14 NOV 2026 (SIMULATED)` in the red margin ink when simulated, plain when real. A test greps `app/` and `scripts/` for banned time calls (§4.6).

### 13.2 Pricing (B, pure)
`price_invoice(lines, discounts, as_of)`. Per line: `line_subtotal = unit_price × qty` → line-scope discount (percent: half-up; fixed: capped at subtotal) → subscription-scope discount on the post-line-discount subtotal, allocated across lines by largest remainder → tax per D-03 → line total. Every step appends to `calc_trace`, for example:

```json
[{"label":"Product price","amount_minor":499900},
 {"label":"Variant: Brand = Odoo","amount_minor":56000},
 {"label":"Unit price","amount_minor":555900},
 {"label":"x 3 seats","amount_minor":1667700},
 {"label":"Discount SEATS10 (10%)","amount_minor":-166770},
 {"label":"Net","amount_minor":1500930},
 {"label":"GST 18% (exclusive)","amount_minor":270167},
 {"label":"Line total","amount_minor":1771097}]
```
Invariant: the signed steps reconcile to the stored line total. A property test checks it.

### 13.3 Billing (B)
Principle: **truth is derived, not cursor-driven.** `expected_periods(...)` is compared with the periods that already have an invoice (including cancelled ones).

`run_billing(as_of, mode, actor_id, auto_confirm, subscription_ids)`:
1. Insert a `billing_runs` row (status running).
2. Candidates = subscriptions with status `active`, OR status `closed AND billing_complete = false`. Load subscriptions, pauses and existing `(subscription_id, period_start, status)` in bulk (3 queries, not per-subscription). The up-to-date path for 8k candidates must finish in under ~20 s.
3. For each candidate compute missing periods without locking. Nothing missing → `up_to_date` (set `billing_complete = true` when closed). Paused periods → noted for `skipped_paused`. Periods that only have a cancelled invoice → `skipped_period_voided`.
4. If periods are missing, open that subscription's OWN transaction:
   ```sql
   SELECT id FROM subscriptions WHERE id = :id FOR UPDATE SKIP LOCKED;
   ```
   No row → `deferred_locked`, retried once at the end of the run. Otherwise recompute missing periods under the lock, then per period (oldest first, max 36 per subscription per run) inside a SAVEPOINT: pick eligible discounts → atomically claim each (§13.5) → price → insert:
   ```sql
   INSERT INTO invoices (...) VALUES (...)
   ON CONFLICT (subscription_id, period_start) WHERE status <> 'cancelled' DO NOTHING RETURNING id;
   ```
   No row returned → we lost a race: roll back to the savepoint (releases the discount claim), `blocked_duplicates += 1`. Then insert lines and redemptions, call `invoices.confirm` if `auto_confirm`, write `audit`. COMMIT. Any exception → that subscription is `failed` with the error text; the run continues.
5. Insert one `billing_run_items` row per candidate (dominant disposition, §11), update `considered`, `invoices_created`, `amount_minor`, set status `completed`, store `integrity_summary = invariants.run_all(...)` result counts.
6. **Dry mode:** same code path, but each subscription's transaction is rolled back instead of committed; the would-be invoices and amounts are collected and stored on the run and items (written in a final separate transaction).
7. **Accounting rule (tested):** `considered == count(items)` and `sum(periods_billed) == invoices_created` (live mode).

`bill_subscription(conn, id, as_of, ...)` is the same per-subscription logic callable inside the caller's transaction; `lifecycle.transition(→ active)` calls it so the first invoice exists immediately.

Why crash-safe: each subscription is atomic; periods are derived from facts; a re-run after a crash finds exactly what is missing.

### 13.4 State machines (B, `domain/state_machines.py` + `services/lifecycle.py`)
- Subscription: `draft→quotation` (send quote: sets `quote_sent_on`, `quote_valid_until`), `quotation→confirmed` (409 if the quote expired), `draft→confirmed` (staff direct confirm), `confirmed→active` (manual, or auto when `start_date <= today` in `run_daily`; calls `bill_subscription`), `active→closed` (early close requires `plan.allow_early_close`; auto-close per D-10). Pause/resume only when Active and `plan.allow_pause`. Renew only when `plan.allow_renew`.
- Optimistic concurrency: `expected_version` mismatch → 409. Invalid transition → 409 with the allowed list.
- Invoice (D): `draft→confirmed` (assign number, set due date), `draft|confirmed→cancelled` (blocked if payments exist; voids redemptions and decrements usage), `confirmed→paid` only via payment posting.

### 13.5 Discount counter (atomic)
```sql
UPDATE discounts SET usage_count = usage_count + 1
 WHERE id = :id AND (usage_limit IS NULL OR usage_count < usage_limit)
RETURNING id;
```
No row → exhausted: drop it and re-price without it. Runs in the same transaction as the invoice insert. The row lock serializes concurrent runs and the WHERE is re-checked after the wait. Invoice cancel voids the redemption and decrements the counter.

### 13.6 Payments (D)
`record(...)`: one transaction: lock the invoice row (`FOR UPDATE`), require status `confirmed`, `amount <= outstanding` (else 422), insert payment (honor idempotency key), update `amount_paid_minor`, set `paid` when equal, `audit`.

### 13.7 Integrity checks (D; SQL independent of engine code)
Period generation in SQL uses arithmetic like `start + (g * interval '1 month')` over `generate_series(0, n)` (never `generate_series` with an interval step, which drifts at month ends), so a bug in the Python period math cannot hide behind the same bug in the checker.

| ID | Check |
|---|---|
| INV-01 | No two non-cancelled invoices share `(subscription_id, period_start)` |
| INV-02 | Per invoice: subtotal, discount, tax and total equal the sums of its lines; per line `total = subtotal - discount (+ tax if exclusive)` |
| INV-03 | `0 <= amount_paid <= total`; `amount_paid = sum(payments)`; status `paid` iff `amount_paid = total` |
| INV-04 | No missing periods: every expected period (recomputed from scratch as of clock today) has an invoice, a recorded void, or a pause covering it |
| INV-05 | `usage_count = count(non-voided redemptions) <= usage_limit` |
| INV-06 | Dashboard figures equal raw recomputation (collected = sum of payments, outstanding, active count, overdue count) |
| INV-07 | Each billing run: `considered = count(items)` |
| INV-08 | Invoice `calc_trace` reconciles to line totals |

---

## 14. RBAC MATRIX (A implements in `permissions.py` as data; every route declares one permission)

| Permission | admin | staff | customer |
|---|---|---|---|
| `catalog:read` | ✓ | ✓ | |
| `catalog:write` (products, variants, plans, taxes, terms, templates) | ✓ | | |
| `discount:read` | ✓ | ✓ | |
| `discount:write` (create/edit rules) | ✓ | | |
| `discount:attach` (attach to a subscription) | ✓ | ✓ | |
| `staff:manage` (create staff users) | ✓ | | |
| `customer:write` | ✓ | ✓ | |
| `sub:read` / `sub:write` (all subscriptions) | ✓ | ✓ | |
| `billing:run` (live and dry-run) | ✓ | ✓ | |
| `invoice:read` / `invoice:write` (all) | ✓ | ✓ | |
| `payment:read` / `payment:write` | ✓ | ✓ | |
| `report:read` (dashboard, overdue, integrity, outbox) | ✓ | ✓ | |
| `clock:admin`, `demo:admin` (DEMO_MODE only) | ✓ | | |
| `portal:own` (own subscriptions, own invoices, own profile) | | | ✓ |

Rules: a role comes from the database, never from the client. Customer-facing queries always filter by `customer_id` from the session. A customer requesting another customer's resource by ID gets **404** (not 403). Portal actions (pause/resume/close/renew) appear only if `lifecycle.allowed_actions` returns them (plan flags). Auth details: argon2id; signed httpOnly SameSite=Lax session cookie (Secure in production); POST requests check `Origin`/`Referer` against `APP_BASE_URL`; reset tokens are 32 random bytes stored as SHA-256 hash, 30-minute expiry, single-use; the reset email is always written to the outbox.

Tests (A): iterate every registered route × role and compare with the matrix (a route with no declared permission fails the build); IDOR tests for subscriptions, invoices and payments; staff cannot hit admin-only endpoints; signup cannot set a role; password boundary tests (exactly 8 fails, 9 passes with all classes).

---

## 15. UI DESIGN SYSTEM — "COUNTING HOUSE LEDGER"

**Idea:** the whole product looks like a bookkeeper's ledger: manila paper, black ink, ruled lines, a red margin rule, rubber-stamp statuses, typewritten numerals. A finance desk, not a SaaS landing page. No JS, no motion, nothing round.

**Tokens (C defines in `ledger.css` `:root`):**
```
--paper: #ECE5D0;  --paper-deep: #E2DAC1;  --ink: #1C1B17;  --ink-soft: #55524A;
--rule: #1C1B17;   --rule-faint: #B9B196;
--margin-red: #A8322A;   /* overdue, voided, errors, simulated-clock, the margin rule */
--stamp-green: #2E5E3E;  /* paid, ok */
--entry-blue: #23405E;   /* links, typed entries */
```
**Type:** body and numbers in IBM Plex Mono 13px (fallback `ui-monospace, "Courier New", monospace`); headings in Source Serif 4 semibold small-caps (fallback Georgia). Load with one Google Fonts `<link>` in `base.html`, fallbacks must look acceptable offline.

**Hard rules (style_lint enforces a subset and fails `make check`):**
- Corners square everywhere: global reset `* { border-radius: 0 !important }` marked `/* style-lint-ok */`; no other `border-radius`.
- No gradients (CSS), no `box-shadow`, no `transition`, no `animation`/`@keyframes`, no `<script>` (one exception: a print button using `window.print()`), no emoji in templates, no icon fonts, no images except none. Charts use inline SVG with hatch `<pattern>` fills, never color gradients.
- No dark mode. No purple, indigo or violet anywhere. No neon. No glass. No card grids. No hero sections. No toasts.
- Banned look (LLM defaults): big rounded cards with sparkline tiles, gradient buttons, pill badges, "Welcome back 👋".

**Layout:** a single sheet, max width ~1180px, paper background, a 1px `--margin-red` vertical rule at the left edge of the content column. Header: product name in small caps, nav as plain text links separated by ` / `, current page underlined; on the right the user, role, and system date. Header ends in a `3px double` rule. Sections are introduced with a numbered small-caps label (`§ 3  Subscriptions`) over a 1px rule. Footer: `FOLIO <path> · set in 14 ms` (request time from middleware).

**Components (C builds as Jinja macros in `_ui.html`; everyone else uses only these):**
- `ledger_table`: header row uppercase 11px with a 2px bottom rule; rows with a faint 1px rule; amounts right-aligned, mono, tabular, always two decimals; negatives in parentheses in `--margin-red`; total row with a 1px top rule and a `3px double` bottom rule. Wide tables scroll horizontally inside their container.
- `stamp(status)`: uppercase 11px text in a rectangular double border. draft = dashed ink-soft; quotation/confirmed = entry-blue; active/paid = stamp-green; overdue/cancelled/void/failed = margin-red. Always text, never colour alone.
- `field`: label in small caps above, input with ONLY a bottom border (like filling in a paper form), transparent background; focus = 2px bottom border plus `--paper-deep` background (instant, no glow). Selects and textareas follow the same rule.
- `button`: rectangular, 1px ink border, uppercase 12px with letter-spacing; primary = ink fill with paper text; destructive = margin-red border and text; hover = inverted colours, instant; disabled = dashed border, faint text.
- `leaders(label, value)`: label, dotted leader line, amount (for KPIs, like a trial balance).
- `stepper(status, history)`: Draft — Quotation — Confirmed — Active — Closed as text with stamps and dates from the audit log.
- `explain(line)`: native `<details><summary>` showing the `calc_trace` as a ledger waterfall.
- Pagination as plain `‹ Prev  Page 3 of 41  Next ›` text links.

**Dashboard:** a "trial balance": KPIs as `leaders` rows (active subscriptions, MRR, collected, outstanding, overdue count and amount). No card tiles. Revenue by month as horizontal SVG hatch bars. Filters are a plain GET form. Every KPI links to the filtered list that produces it, and the list total must equal the KPI.

**Invoice print view:** A4, ink only, no chrome, ledger rules, real invoice layout (`@media print`).

**Copy tone:** plain, accounting vocabulary ("Debit", "Folio", "Entered", "Posted") used sparingly where natural; empty states say what to do next; destructive actions use a confirm page, not a modal.

---

## 16. PAGE MAP

Public/auth (A): `/login`, `/signup`, `/forgot`, `/reset/{token}`, `/logout`.
Portal (A): `/portal`, `/portal/subscriptions/{id}`, `/portal/invoices`, `/portal/invoices/{id}` (printable), `/portal/profile`.
Staff app: `/app` dashboard (D) · `/app/subscriptions`, `/new`, `/{id}` (C) · `/app/customers` (C) · `/app/invoices`, `/{id}`, `/{id}/print` (D) · `/app/payments` (D) · `/app/overdue` (D) · `/app/billing-runs`, `/{id}` (A page, B logic) · `/app/integrity` (D) · `/app/outbox` (A) · `/app/clock` (A) · `/app/users` (A, admin) · `/app/catalog/{products,plans,taxes,terms,templates,discounts}` (C) · `/styleguide` (C, dev).
Other: `/health` (A), `/internal/daily` POST with header `X-Cron-Token` (B).

---

## 17. TASKS BY OWNER (A writes these into `docs/tasks/<handle>.md` and creates GitHub issues from them in task A-09). `~min` = rough agent+human minutes. Tier 0 = required, Tier 1 = should, Tier 2 = nice.

### A — Lead (base, access, integration)
**Phase 0a (T+0:00–0:25) → tag `base-0a`:**
- A-01 (10) Scaffold: dirs, `requirements.txt`, `Makefile` (all targets §7), `docker-compose.yml` (Postgres 16), `.env.example`, `.gitignore`, `ruff` config, `.editorconfig`.
- A-02 (10) `000_base_schema.sql` from §11, `app/migrate.py` (applies all unapplied files, order by filename), `app/db.py`, `config.py`.
- A-03 (5) `main.py` with auto-discovery of `routes/*.py` and `NAV`, `/health`, minimal `base.html`.
- A-04 (10) All contract stubs from §12 with docstrings, `deps.require()` with `DEV_AUTH_BYPASS=1` returning a fake admin until A-07, `check_stubs.py`, `style_lint.py` skeleton.
- A-05 (10) `.github/workflows/ci.yml` (Postgres service; install; migrate; ruff; style-lint; pytest), PR template, CODEOWNERS, copy of this plan to `docs/BUILD_PLAN.md`, `AGENTS.md` and `CLAUDE.md` (§4 verbatim + pointer), draft `README.md`, empty `docs/log/*.md`, `docs/tasks/*.md`, `requirements.yaml`. Push, tag `base-0a`, tell the team.

**Phase 0b (T+0:25–0:55) → tag `base-v1`:**
- A-06 (10) `clock.py` + table-backed state + `money.py` (fmt/parse/round) + tests + the banned-time grep test.
- A-07 (20) Auth: signup with password rules, unique email, login/logout, forgot/reset via outbox (`outbox.queue_email`), argon2id, signed session cookie, `require(permission)`, `permissions.py` matrix, admin seed from env, `queue_email`, `audit`.
- A-08 (5) `base.html` wired to `ledger.css` (C's), nav built from `NAV` by role, clock line, footer timing middleware.
- A-09 (10) `scripts/gh_bootstrap.py` (uses `gh`): labels (`owner:A..D`, `tier:0/1/2`, `request`, `blocked`, `contract-change`, `decision`, `unassigned`, `freeze-fix`), milestones per gate, issues from the task files, branch protection on `main`. Tag `base-v1`.

**Phase 1 (after G1):**
- A-10 (25) Tier 0: staff users page (admin creates staff), RBAC matrix test over all routes, IDOR tests.
- A-11 (40) Tier 0: portal (own subscriptions with allowed actions via `lifecycle.allowed_actions`, own invoices, printable invoice using D's partial, profile).
- A-12 (15) Tier 0: `/app/clock` page (advance day/week/month, set date, reset; DEMO_MODE only) calling `lifecycle.run_daily`.
- A-13 (15) Tier 0: `/app/outbox` page (rendered body, clickable link).
- A-14 (35) Tier 0: billing-run pages: list, run form (as-of defaults to clock today, dry-run / live / "confirm invoices immediately" checkbox), result page (header counts, integrity summary, disposition table filterable and searchable by subscription). Tier 1: "Confirm all drafts from this run" via `invoices.confirm_many`, "Hammer it" button via `chaos.hammer`.
- A-15 (30) Tier 0: `scripts/seed_demo.py` (small, hand-authored realistic dataset, §18), `SEED_ON_BOOT`, `make reset-demo`, `/app/demo/reset` (DEMO_MODE).
- A-16 (30) Tier 0: e2e test `tests/e2e/test_month.py` (the G2 path) and later the full demo-script path.
- A-17 (40) Tier 0: finalize `README.md` (verify every claim), `docs/DECISIONS.md`, `docs/JUDGE_QA.md`, demo rehearsal, backup video, fresh-clone test, `style_lint.py` complete.
- **Standing duty:** merge captain: at every sync window check open PRs, run `make check` on `main`, post `make status`, tag gates, watch `git shortlog -sn`, assign `unassigned` issues.

### B — Engine
**Prep (T+0:00, no dependencies, pure code in `app/domain/`):**
- B-01 (15) `periods.py` (anchor-relative month/year math with month-end clamping, leap years, pauses, closed_on, cap) + tests.
- B-02 (25) `pricing.py` and tax math (D-02, D-03, largest-remainder allocation, `calc_trace` that reconciles) + property tests (`sum(lines) == totals`, discount ≤ subtotal, never negative).
- B-04 (10) `state_machines.py` tables + tests.
- B-03 (15) `discounts.py` selection (eligibility, best-per-line, one subscription-scope, tie-breaks) + tests.
**After base-0a:**
- B-07 (30) Tier 0: `lifecycle.py` (all transitions, plan flags, quote validity, optimistic version, pause history, renew, `allowed_actions`, `run_daily` auto-activate and auto-close) + tests.
- B-05 (40) Tier 0: `bill_subscription` (§13.3 per-subscription logic, atomic discount claim, calc_trace stored, audit) + tests.
- B-06 (40) Tier 0: `run_billing` (candidates, bulk load, dispositions, SKIP LOCKED, deferred retry, dry-run via rollback, accounting rule, integrity summary).
- B-09 (30) Tier 0: engine tests on real Postgres: run 3× → no duplicates; 4 concurrent threads; discount limit race (limit 1, 8 concurrent runs → exactly 1 use); crash mid-run then re-run → no gap/no duplicate; pause/void/catch-up dispositions; `considered == items`.
- B-11 (10) Tier 1: `jobs/daily.py` + `/internal/daily` guarded by `CRON_TOKEN`.
- B-10 (20) Tier 1: `chaos.hammer` (N concurrent live runs per round, advance the clock one period between rounds; returns created / duplicates found (must be 0) / blocked_duplicates / invariants).
- B-12 (15) Tier 1: `preview_next_invoice(conn, sub_id)` via dry-run for subscription pages.
- B-13 (30) Tier 2: randomized month-simulation test (random sequences of clock advances, runs, pauses, closes, payments; invariants checked after every step).

### C — Catalog, subscriptions, design system
**Prep (T+0:00, no dependencies):**
- C-01 (45) Tier 0: `ledger.css` + `_ui.html` macros (§15) + `/styleguide` page showing every component. Push this FIRST; A needs it for `base.html`.
**After base-0a:**
- C-02 (50) Tier 0: catalog services and pages: taxes, payment terms, products (+ variants with extra price, notes), plans (interval, min quantity, availability, flags), plan price overrides, `resolve_unit_price`, `build_line_snapshot`.
- C-03 (15) Tier 0: customers list, create, edit (search, pagination).
- C-04 (25) Tier 0: quotation templates (plan, lines, validity).
- C-05 (60) Tier 0: `subscription_builder` (create manually or from template, line snapshots, min-quantity and plan-availability validation) and pages: list (filters by status, customer, plan; search; server-side pagination), new, detail (stepper from audit log, lines, invoices of this subscription, allowed-action buttons calling `lifecycle`, discount attach). Draft-only line editing.
- C-06 (30) Tier 0: discount rules admin (admin-only): kind, value, min purchase or quantity, dates, usage limit, scope and product; list and detail with usage count.
- C-07 (30) Tier 1: UI consistency pass across ALL pages in the hardening window (macros only, empty states, error states, print CSS).

### D — Money, reporting, ops
**Prep (T+0:00, no dependencies):**
- D-01 (35) Tier 0: invariant SQL files in `db/queries/` (INV-01..08 from §13.7) and `services/invariants.py::run_all`; test them against fixtures once the schema lands.
**After base-v1:**
- D-09 (25) Tier 0 (do first): `Dockerfile`, `render.yaml` (web service + Postgres), start command `python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT`, deploy the skeleton, confirm a public URL, write `docs/log/d.md`. Retire deployment risk NOW.
- D-02 (50) Tier 0: `invoices.py` (list with filters, get, confirm with number and due date, `confirm_many`, cancel with redemption void, send to outbox, `get_for_customer`) + pages (list, detail with per-line `explain`, print view and a reusable `invoice_print.html` partial for the portal).
- D-03 (30) Tier 0: `payments.py::record` (§13.6) + pages (record form on the invoice, payments list, outstanding column).
- D-04 (45) Tier 0: `reports.py` + dashboard (§15), overdue list with "send reminder" (writes to outbox), filters, drill-through lists whose totals equal the KPIs.
- D-05 (15) Tier 0: `300_d_indexes.sql` + query-count assertions for list and dashboard endpoints.
- D-06 (35) Tier 0: `seed_scale.py`: ≥ 8,000 subscriptions, ~60k invoices, ~40k payments via SQL bulk inserts (`generate_series`), then run all invariants; must be green.
- D-07 (20) Tier 0: `perf_check.py` (hit every list and dashboard endpoint 30× as staff; write p50/p95 to `docs/PERF.md` with EXPLAIN for the 3 heaviest queries). Budget p95 < 500 ms server time; hard limit 2 s.
- D-08 (10) Tier 1: `301_d_invoice_immutability.sql` trigger (D-14).
- D-10 (15) Tier 1: `/app/integrity` page: green/red per check, violation count, sample rows, "Run now".
- D-11 (15) Tier 2: aging buckets (0–30, 31–60, 61–90, 90+) on the dashboard.

---

## 18. SEED AND DEMO

**`make seed` (small, hand-authored, believable; A builds):** 1 admin, 2 staff, ~25 customers (realistic Indian small-business names), 6 products (ERP Suite with Brand variants Odoo +560.00, Zoho +0.00, Tally +240.00; CRM; Books; Analytics add-on; Support add-on; one product without variants), 4 plans (monthly, yearly, weekly trial, one with `auto_close` and a near end date), 3 taxes (GST 18% exclusive, GST 5% exclusive, one inclusive), payment terms (Immediate, Net 15, Net 30), 3 quotation templates, 3 discounts (10% on ≥ 5 seats, fixed 500 off ≥ 5,000, one already expiring), ~60 subscriptions across all states with history so the dashboard is non-empty. The demo account credentials go in README. The seed must run through the real services where cheap, and direct SQL elsewhere; all invariants must be green afterward.

**Demo script, 6 minutes ("A Month at Brightloop"; A owns and rehearses it):**
0. 20 s: pitch line ("every number explains itself, and the system proves it never double-bills"). Point at the system-date line.
1. **Signup:** weak password rejected (exactly 8 chars shows the rule), duplicate email rejected, forgot password → Outbox → click link → reset. Log in as a customer; try another customer's invoice URL → 404.
2. **Launch a plan (admin):** product with Brand = Odoo (+560), a monthly plan with flags, a tax. Show staff cannot create a discount or a staff user.
3. **Quote → subscription:** template → quote → confirm → activate; stepper; first invoice with the Explain waterfall showing +560.
4. **Billing day:** advance the clock. Dry-run ("N will be billed, M paused, K voided"). Run billing → N invoices (confirm immediately checked). Run AGAIN → 0 created. Search one subscription in the disposition table to show a reason. (If B-10 is done: "Hammer it" shows duplicates blocked, integrity still green.)
5. **Discount:** admin creates "10% on ≥ 5 seats, limit 3" → next run applies it automatically; once the limit is used up, later invoices don't get it; advance the clock past its end date → stops.
6. **Money in:** partial payment (method, note), then the remainder → Paid. Advance the clock → overdue appear → send reminder → Outbox.
7. **Finance lead:** dashboard on the 8k dataset with filters, footer showing milliseconds, drill from Overdue into the list (counts match). Open `/app/integrity` (all green). Open `docs/PERF.md` numbers.
8. 20 s close: what we deliberately did not build (§21).

Record a backup video of the whole script. Keep `docker compose up` + `make seed` as the offline fallback.

---

## 19. TESTS REQUIRED (minimum bar)

- **Unit (pure):** period math (month-end clamping, leap year, week/day/year, large k), money rounding, tax inclusive and exclusive, largest-remainder allocation, discount selection and stacking, state machine tables, password validation boundaries, money formatting.
- **Integration (real Postgres):** run billing three times → no duplicates; concurrent runs; discount limit race; crash mid-run then re-run; payment partial and over-payment rejection; payment race; quote expiry; plan flags enforced; pause/close/renew; dispositions accounting; auto-close.
- **Authz:** route × role matrix, IDOR, signup cannot set role, admin-only staff creation and discount creation.
- **E2E (HTTP):** the G2 path, then the full demo-script path.
- **Perf:** query-count caps on list and dashboard endpoints; `make perf` numbers recorded.
- **Hygiene:** banned-time grep, style lint, stub report.
- Tests must be able to fail. When adding a guard, also write the test that proves the unguarded behavior was possible.

---

## 20. CUT LADDER AND RISKS

**Cut order when behind (bottom first). Never cut Tier 0.**
- Tier 0: every R-* requirement; Clock; dispositions; basic integrity (INV-01, 02, 03, 05, 06, 07); server-side RBAC; scale seed with perf under budget; deployed URL; README.
- Tier 1: explain UI; dry-run; chaos button; "confirm all drafts"; immutability trigger; integrity page polish; preview next invoice; daily job endpoint.
- Tier 2: aging buckets; randomized month-simulation test; re-issue UI; SMTP delivery (keep outbox); rate limiting.

**Top risks and counters:**
1. *Integration surprises at G2.* Counter: contract stubs from base-0a, A's e2e test written early, sync windows, small PRs.
2. *Merge conflicts.* Counter: ownership map, auto-registered routers, per-owner migrations/logs/tasks.
3. *Agent claims not backed by runs.* Counter: rule 4, paste the final output line in logs and PRs, CI on every PR.
4. *B is the critical path.* Counter: B starts pure code at T+0; A and D take everything non-engine; if B slips by 30 minutes at G2, A pairs on `bill_subscription` and cuts Tier 1 immediately.
5. *Deploy surprises.* Counter: D deploys the skeleton by T+1:20, redeploys on every gate tag.
6. *Style drift across four agents.* Counter: `_ui.html` macros only, `style_lint` in CI, C's consistency pass.
7. *Time overrun.* Counter: freeze at T+4:30 is absolute.

---

## 21. DEFINITION OF DONE AND DELIBERATE OMISSIONS

**Done at submission:** fresh clone → `make db-up setup migrate seed dev` works in under 5 minutes; public URL up with demo credentials in the README; every R-ID has a passing test or an honest line under "Known limitations" in the README; integrity all green on the scale dataset; `docs/PERF.md` has real numbers; `make check` green on `main`; backup video recorded; demo rehearsed 3×; every member has merged PRs.

**`docs/JUDGE_QA.md` (A drafts from the code, the whole team rehearses):** how we guarantee no double billing (partial unique index + per-subscription transaction + row lock + same-transaction discount claim); what happens if a run crashes (atomic per subscription, periods derived from facts); how we know nothing is skipped (dispositions plus INV-04/INV-07); tax and rounding (D-02, D-03); pause/close/renew behaviour; how we know the dashboard is right (INV-06, drill-through equality); how customer isolation is tested; how this scales (partition invoices, move runs to a queue, SKIP LOCKED already allows multiple workers); what we did not build and why.

**Deliberately NOT built (say it on the last slide; it shows judgment):** payment gateway integration, proration and refunds, multi-currency, dunning automation, multi-tenant organizations, JS framework.

---

## 22. KICKOFF PROMPTS (each human pastes ONE into their own agent)

**A:** "You are agent A (lead). Read docs/BUILD_PLAN.md fully. Follow §4 and §5. Execute tasks A-01 to A-05 NOW, then tag base-0a and push. Then A-06 to A-09, tag base-v1. Keep docs/log/a.md updated. Do not touch files you don't own."

**B:** "You are agent B (engine). Pull main and read docs/BUILD_PLAN.md fully. Follow §4 and §5. Start B-01, B-02, B-04, B-03 immediately as pure code in app/domain/ with tests; they need nothing else. Once base-0a is tagged, continue with B-07, B-05, B-06, B-09 in that order. Branch per task, small PRs, log in docs/log/b.md."

**C:** "You are agent C (catalog and UI). Pull main and read docs/BUILD_PLAN.md fully, especially §15 (style law). Start C-01 immediately: ledger.css, _ui.html macros and /styleguide, and push it first. After base-0a, continue C-02 to C-06 in order. Branch per task, small PRs, log in docs/log/c.md."

**D:** "You are agent D (money and reporting). Pull main and read docs/BUILD_PLAN.md fully. Start D-01 immediately (invariant SQL from §13.7). After base-v1, do D-09 (deploy the skeleton) first, then D-02 to D-07 in order. Branch per task, small PRs, log in docs/log/d.md."