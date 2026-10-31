# Tasks — D (money, reporting, ops)

Legend: `- [ ] D-01 (35) ...` — rough minutes. Tier 0 unless marked.

## Prep (T+0:00, no dependencies)

- [ ] D-01 (35) Tier 0: invariant SQL files in `db/queries/` (INV-01..08 from §13.7) and `services/invariants.py::run_all`; test them against fixtures once the schema lands.

## After base-v1

- [ ] D-09 (25) Tier 0 (do first): `Dockerfile`, `render.yaml` (web service + Postgres), start command `python -m app.migrate && uvicorn app.main:app --host 0.0.0.0 --port $PORT`, deploy the skeleton, confirm a public URL, write `docs/log/d.md`. Retire deployment risk NOW.
- [ ] D-02 (50) Tier 0: `invoices.py` (list with filters, get, confirm with number and due date, `confirm_many`, cancel with redemption void, send to outbox, `get_for_customer`) + pages (list, detail with per-line `explain`, print view and a reusable `invoice_print.html` partial for the portal).
- [ ] D-03 (30) Tier 0: `payments.py::record` (§13.6) + pages (record form on the invoice, payments list, outstanding column).
- [ ] D-04 (45) Tier 0: `reports.py` + dashboard (§15), overdue list with "send reminder" (writes to outbox), filters, drill-through lists whose totals equal the KPIs.
- [ ] D-05 (15) Tier 0: `300_d_indexes.sql` + query-count assertions for list and dashboard endpoints.
- [ ] D-06 (35) Tier 0: `seed_scale.py`: >= 8,000 subscriptions, ~60k invoices, ~40k payments via SQL bulk inserts (`generate_series`), then run all invariants; must be green.
- [ ] D-07 (20) Tier 0: `perf_check.py` (hit every list and dashboard endpoint 30x as staff; write p50/p95 to `docs/PERF.md` with EXPLAIN for the 3 heaviest queries). Budget p95 < 500 ms server time; hard limit 2 s.
- [ ] D-08 (10) Tier 1: `301_d_invoice_immutability.sql` trigger (D-14).
- [ ] D-10 (15) Tier 1: `/app/integrity` page: green/red per check, violation count, sample rows, "Run now".
- [ ] D-11 (15) Tier 2: aging buckets (0-30, 31-60, 61-90, 90+) on the dashboard.
