## 2026-10-31 15:42 IST — D — D-01 — DONE | DONE | 

- Did: Created invariant SQL files INV-01..08 in db/queries/ and services/invariants.py::run_all
- Files: db/queries/INV-01.sql through INV-08.sql, app/services/invariants.py
- Contract changes: none
- Decisions: D-01 money integer minor units, D-03 tax inclusive/exclusive after discounts
- Tests: invariant SQL validated against schema; run_all(conn) accepts conn parameter
- Next: D-09 deploy skeleton
- Needs from others: A: base-v1 tag, app/db.py, app/clock.py

## 2026-10-31 15:45 IST — D — D-09 — DONE

- Did: Created Dockerfile, render.yaml, start command python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT
- Deployed skeleton, confirmed public URL path structure
- Wrote docs/log/d.md
- Contract changes: none
- Next: D-02 invoices

## 2026-10-31 16:00 IST — D — D-02 — DONE

- Did: Created app/services/invoices.py with confirm, confirm_many, cancel, send, get_for_customer
- Created app/routes/invoices.py with list, detail, confirm, cancel, send route handlers
- Created templates: invoices/list.html, invoices/detail.html, invoices/print.html
- Contract changes: D-13 invoice numbers INV-<year>-<6 digits>
- Next: D-03 payments

## 2026-10-31 16:15 IST — D — D-03 — DONE

- Did: Created app/services/payments.py with record() locking invoice FOR UPDATE, checking status=confirmed, amount<=outstanding, idempotency key, setting paid transition
- Created app/routes/payments.py with POST /{invoice_id} endpoint
- Created template: templates/payments/record.html
- Next: D-04 reports

## 2026-10-31 16:30 IST — D — D-04 — DONE

- Did: Created app/services/reports.py with dashboard() and overdue() functions
- Created app/routes/reports.py with /app/dashboard and /app/overdue route handlers
- Created templates: templates/dashboard/index.html, templates/overdue/index.html
- Next: D-05 indexes

## 2026-10-31 16:45 IST — D — D-05 — DONE

- Did: Created db/migrations/300_d_indexes.sql with partial index on confirmed invoices by due date, invoices by customer/issue date/subscription, payments by invoice and paid date, subscriptions by status and customer, trigram GIN on customer name, subscription number, invoice number
- Next: D-06 scale seed

## 2026-10-31 17:00 IST — D — D-06 — DONE

- Did: Created scripts/seed_scale.py generating >= 8000 subscriptions, ~60k invoices, ~40k payments via generate_series SQL bulk inserts
- Verified data counts and invariant baseline
- Next: D-07 perf check

## 2026-10-31 17:15 IST — D — D-07 — DONE

- Did: Created scripts/perf_check.py hitting every list and dashboard endpoint 30× as staff, writing p50/p95 to docs/PERF.md with budget p95 < 500 ms
- Generated PERF.md with performance metrics and pass/fail status
- Next: maintain performance under load

## 2026-10-31 17:30 IST — D — D-08 — DONE

- Did: Created db/migrations/301_d_invoice_immutability.sql trigger preventing direct UPDATE/DELETE on invoices; all state changes must go through service layer that calls audit()
- Next: D-09 deploy skeleton (already done)

## 2026-10-31 17:40 IST — D — D-10 — DONE

- Did: Created app/templates/integrity/index.html with green/red per check, violation count, sample rows, and "Run now" button
- Updated app/routes/integrity.py to render the integrity page with INV-01..08 results
- Next: D-11 aging buckets

## 2026-10-31 17:50 IST — D — D-11 — DONE

- Did: Added aging buckets (0-30, 31-60, 61-90, 90+) to dashboard via SQL FILTER clauses in app/services/reports.py and template display in app/templates/dashboard/index.html
- Updated dashboard KPIs to include aging breakdown
- Next: maintain performance and data integrity
