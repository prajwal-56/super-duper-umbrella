# Brightloop Ledger

A subscription management system for a company that earns its money every month: products and plans, quotations, subscriptions, automatic recurring invoices, payments, and a finance view. Everything runs from one place, with a customer portal on the side.

## What makes it different

- **Simulated clock.** Walk through a whole billing month in minutes. All business logic reads time from one module.
- **Billing-run ledger.** Every subscription in a run gets a recorded outcome and reason (billed, up to date, paused, voided, failed). Nothing is skipped silently. Dry-run uses the exact live code path.
- **Never billed twice.** Enforced by the database (unique invoice per subscription period), per-subscription transactions and row locks, and tested with concurrent runs.
- **Integrity page.** Independent SQL checks (duplicates, gaps, totals, discount counters, dashboard vs raw data) that stay green.
- **Explain every number.** Each invoice line stores a calculation trace: base price, variant extra, discount, tax.
- **Fast.** Tested on 8,000+ subscriptions. Every page shows how long it took to render. See `docs/PERF.md`.

## Roles

| Role | Can do |
|---|---|
| Admin | Everything: catalog, taxes, discount rules, staff accounts, billing, clock |
| Staff | Day-to-day: customers, subscriptions, billing runs, invoices, payments, reports |
| Customer | Own subscriptions and invoices through the portal |

Demo accounts (after `make reset-demo`):

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `Brightloop#2026` |
| Staff | `staff1@example.com` | `Brightloop#2026` |
| Customer | `contact@tata-motors-pune.co.in` | `Customer#2026!` |

## Quick start (local)

Requirements: Python 3.12, Docker (for Postgres 16) or any local Postgres, `make`. On Windows use WSL2.

```bash
git clone <repo-url> && cd <repo>
cp .env.example .env          # set SECRET_KEY, ADMIN_PASSWORD
make db-up                    # Postgres in Docker
make setup                    # virtualenv + dependencies
make migrate                  # create the schema
make seed                     # small demo dataset
make dev                      # http://localhost:8000
```

Optional: `make seed-scale` loads 8,000+ subscriptions for performance testing. `make invariants` prints the integrity checks. `make reset-demo` restores the small demo dataset.

## How to use it

**As a customer:** sign up (password: more than 8 characters with an uppercase letter, a lowercase letter and a special character; one account per email). Open the portal to see your subscriptions and invoices, and pause, resume or close a subscription where the plan allows it. Forgot your password? A reset link is sent to your registered email (in development it appears under **Outbox**).

**As admin:** create taxes, payment terms, products (with variants such as brand, which can add to the price), plans (billing period, minimum quantity, availability dates, and whether the plan auto-closes or can be paused, closed early or renewed), quotation templates and discount rules. Add staff accounts under Users.

**As staff:** create a subscription (from a template or manually): Draft → Quotation → Confirmed → Active. On billing day open **Billing runs**, preview with a dry-run, then run billing. Invoices are created with customer details, lines, discounts and taxes already filled in. Confirm, send or print them. Record payments (method, amount, date, note) against invoices; partial payments are supported.

**As the finance lead:** the dashboard shows active subscriptions, MRR, collected revenue, outstanding amounts and overdue invoices with filters. Click any figure to see the invoices behind it.

**Demo mode** (`DEMO_MODE=true`): admin gets a **Clock** page to move the system date forward, plus a reset button. The system date is always shown in the page header, and marked when simulated.

## Business rules (short)

Amounts are stored as integers in minor units. Billing is in advance, anchored to the subscription start date (so Jan 31 → Feb 28 → Mar 31 without drift). Tax is calculated after discounts, per tax rule (inclusive or exclusive). Discounts apply automatically to the next invoice and stop at their end date or usage limit. An invoice is overdue when it is confirmed, unpaid and past its due date. Full list of decisions: `docs/DECISIONS.md`.

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `TEST_DATABASE_URL` | Separate database for tests |
| `SECRET_KEY` | Signs session cookies. Use a long random value |
| `APP_BASE_URL` | Public URL (used in emailed links and request checks) |
| `DEMO_MODE` | `true` enables the clock and reset tools. Use `false` for a real deployment |
| `SEED_ON_BOOT` | `true` loads demo data on first start when the database has no users |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First admin account |
| `CRON_TOKEN` | Secret for the optional daily job endpoint |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | Optional. Without them emails are only stored in the Outbox |
| `CURRENCY_CODE`, `BUSINESS_TZ` | Defaults `INR`, `Asia/Kolkata` |

## Project layout

```
app/        FastAPI app: domain/ (pure logic), services/ (database logic), routes/, templates/, static/
db/         migrations/ (plain SQL) and queries/
scripts/    seed_demo, seed_scale, perf_check, style_lint
tests/      unit, integration (real Postgres), authz, e2e
docs/       BUILD_PLAN, DECISIONS, PERF, JUDGE_QA, per-person logs
```

Stack: Python, FastAPI, Jinja2 (server-rendered, no JavaScript framework), PostgreSQL, psycopg.

## Testing

```bash
make check      # lint + style lint + tests (needs the test database)
make test
make perf       # writes numbers to docs/PERF.md
```

Billing tests run against a real Postgres (concurrent runs, crash recovery, discount limit races). Access tests check every route against the role matrix and try cross-customer access by direct URL.

## Hosting

**Render (recommended, uses the included `render.yaml`):**
1. Push the repo to GitHub.
2. In Render: **New → Blueprint**, pick the repo. It creates a web service and a Postgres database.
3. Set environment variables on the web service: `SECRET_KEY` (random), `APP_BASE_URL` (your Render URL), `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEMO_MODE` (`true` for a demo, `false` otherwise), `SEED_ON_BOOT=true` for a demo. `DATABASE_URL` is wired automatically.
4. Deploy. The start command applies migrations, then starts the server (`python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
5. Open `/health` to confirm it is up.

Free-tier notes (as documented by Render in October 2026; check current limits before relying on them): a free web service spins down after 15 minutes without traffic and takes about a minute to wake, and free Postgres databases expire 30 days after creation. **Open the site a few minutes before a demo** so it is awake, and move to a paid instance and database for anything real.

**Any other host (Docker):**
```bash
docker build -t brightloop-ledger .
docker run -p 8000:8000 --env-file .env brightloop-ledger
```
Point `DATABASE_URL` at any managed Postgres (14+). Run `python -m app.migrate` once before the first start.

**Daily billing job (optional):** `POST /internal/daily` with header `X-Cron-Token: <CRON_TOKEN>` runs lifecycle updates (auto-activate, auto-close) and the billing run. Trigger it from any scheduler, for example a scheduled GitHub Actions workflow with `curl`.

## Known limitations

No payment gateway (payments are recorded manually), no proration or refunds, single currency, invoice numbers may have gaps, cancelled billing periods are not re-billed automatically. See `docs/DECISIONS.md`.

## Team

| Handle | Focus |
|---|---|
| A | Base, auth and access control, portal, clock, integration |
| B | Billing engine, discounts, subscription lifecycle |
| C | Catalog, subscriptions, design system |
| D | Invoices, payments, reports, integrity, performance, deployment |

Work is tracked through GitHub issues and pull requests; `docs/log/` has each person's running log.

## License

MIT