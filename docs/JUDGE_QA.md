# Judge Q&A & Technical Defense Guide

This document captures the architectural decisions, invariant proofs, and answers to common technical and domain questions for judges reviewing the **Brightloop Ledger** billing and subscription management platform.

---

### 1. How do you guarantee that a subscription is never double-billed?
We enforce non-duplication at four complementary layers:
1. **Database Schema Constraints:** A partial unique index on non-cancelled invoices: `UNIQUE (subscription_id, period_start) WHERE status != 'cancelled'` guarantees at the PostgreSQL engine level that two active/confirmed invoices can never exist for the exact same subscription billing period.
2. **Deterministic In-Advance Fact Derivation:** Expected billing periods are derived purely from immutable business facts (subscription `start_date`, plan interval/count, pause intervals, and `closed_on` date). We do not store an ad-hoc "next_billing_date" that could drift or be corrupted.
3. **Concurrency Control & Row Locking:** Billing runs process candidate subscriptions using `SELECT ... FOR UPDATE SKIP LOCKED` inside per-subscription isolated transactions. Even if multiple billing worker threads or daily cron runs trigger simultaneously, only one worker can process a given subscription period.
4. **Invariant Assertion (INV-01):** The database integrity suite continuously verifies:
   ```sql
   SELECT subscription_id, period_start, COUNT(*)
   FROM invoices
   WHERE status != 'cancelled'
   GROUP BY subscription_id, period_start
   HAVING COUNT(*) > 1;
   ```
   Zero violations are permitted across any test or live environment.

---

### 2. What happens if a billing run crashes mid-execution?
1. **Atomic Per-Subscription Transactions:** Each candidate subscription in a billing run is processed and committed in its own database transaction (`run_billing`). A crash on subscription #42 leaves subscriptions 1..41 fully committed, while #42 rolls back completely to its pre-billing state.
2. **Resumption Without Duplicate Gaps:** Because periods are derived from chronological facts and existing invoice records in the database, re-running billing simply inspects what periods are missing an invoice. Subscriptions 1..41 will be marked with disposition `up_to_date` and skipped with zero duplicate charges, and subscription #42 will be cleanly picked up and invoiced.
3. **Crash Recovery Stress Test:** Verified under automated chaos tests (`tests/engine/test_chaos.py` and `tests/engine/test_run_billing.py`), which simulate mid-run worker crashes and verify zero period gaps and zero duplicate invoices upon recovery.

---

### 3. How do you know no eligible subscription was silently skipped?
1. **Explicit Billing Ledger Dispositions:** Every candidate considered in a billing run records an explicit row in `billing_run_items` detailing its disposition:
   - `billed`: Invoice generated and linked.
   - `up_to_date`: All derived periods already invoiced through target date.
   - `paused`: Subscription was paused during the evaluated period.
   - `voided`: Period voided due to mid-period cancellation or closure.
   - `failed`: Explicit error message recorded without blocking other candidates.
2. **Integrity Reconciliation (INV-04 & INV-07):**
   - **INV-04:** Verifies that every expected active period between `start_date` and current simulation date contains either an invoice, a logged pause interval, or a closure record.
   - **INV-07:** Verifies that the header candidate count of every `billing_runs` row exactly equals the count of logged `billing_run_items`.

---

### 4. How are taxes and rounding handled across line items?
1. **Integer Minor Units:** All monetary values (`sales_price_minor`, `unit_price_minor`, `subtotal_minor`, `tax_minor`, `total_minor`) are stored and computed strictly as 64-bit integers (`BIGINT` in PostgreSQL, `int` in Python). Floats are strictly prohibited.
2. **Banker's Rounding for Tax Calculations:** Tax calculation uses standard half-to-even rounding (`(amount * rate_bps + 5000) // 10000`).
3. **Inclusive vs. Exclusive Tax Support:**
   - Exclusive Tax: Subtotal is pre-tax; tax is calculated and added onto subtotal.
   - Inclusive Tax: Line unit price already includes tax; taxable base is extracted via `(gross * 10000) // (10000 + rate_bps)`, ensuring the sum of tax and taxable base reconciles exactly to the line total without rounding leakage.
4. **Audit Traceability (INV-02 & INV-08):** Invoices record full per-line snapshots and JSON `calc_trace` reconciling line-level computations directly to aggregate invoice headers.

---

### 5. How are subscription discounts and race conditions managed?
1. **Atomic Claim in Transaction:** Discount redemptions are recorded in `discount_redemptions` within the same transaction that generates the invoice.
2. **Concurrency Safe Usage Limits (INV-05):** When a discount has a finite `usage_limit`, billing updates and checks the discount record using row locking (`FOR UPDATE`) to ensure concurrent threads cannot claim a discount beyond its configured limit. Tested by 8 concurrent billing threads competing for a single redemption limit in `tests/engine/test_run_billing_concurrency.py`.
3. **Cancellation Voiding:** If an invoice with an applied discount is cancelled, the associated `discount_redemptions` row is marked `is_void = true`, safely freeing redemption capacity where applicable.

---

### 6. How do you guarantee the Executive Dashboard figures are accurate?
1. **INV-06 Invariant Enforcement:** The `/app/integrity` suite runs automated checks comparing dashboard aggregates (MRR, Total Collected, Total Outstanding, Overdue Totals) against raw line-level database queries across all customer accounts.
2. **Strict Drill-Through Equality:** Every number on the dashboard links directly to the underlying filtered ledger view (e.g. Overdue count links to `/app/overdue`), and the sum of rows in the drill-through view equals the KPI figure on the dashboard.

---

### 7. How is tenant isolation and security enforced?
1. **Server-Side Authorization (`require` dependencies):** Every endpoint declares required role permissions (`subscription:read`, `invoice:write`, `report:read`, etc.). Hiding UI buttons is treated as cosmetic; authorization is enforced in Python before service execution.
2. **Customer Portal IDOR Protection:** Customer portal routes strictly filter queries by `customer_id` derived directly from the authenticated session cookie (`user.customer_id`), preventing horizontal authorization traversal (tested comprehensively in `tests/authz/test_portal_idor.py`).
3. **Audit Trail Immutability:** Sensitive state transitions and money operations write immutable rows to `audit_log`, protected by PostgreSQL triggers blocking modification.

---

### 8. How does this system scale?
1. **Stateless App Tier:** The FastAPI application layer is completely stateless and horizontally scalable behind any standard HTTP load balancer.
2. **PostgreSQL SKIP LOCKED Processing:** Multiple billing workers can execute concurrently without colliding or deadlocking on subscriptions.
3. **Optimized Indexes:** Full B-Tree and partial indexes cover foreign keys, subscription status, invoice dates, and portal customer lookups (`db/migrations/300_d_indexes.sql`).
4. **Future Scale Vectors:** Invoices can be partitioned by `period_start` year/month, and billing candidate generation can be dispatched to asynchronous message queues (e.g. pg_amqp or worker pools).

---

### 9. What was deliberately NOT built and why?
1. **Third-Party Payment Gateways (Stripe/Razorpay SDKs):** We intentionally implemented direct ledger payment recording with multi-method tracking (Bank Transfer, UPI, Cheque, Cash) to keep all financial invariants testable offline and self-contained without external mock fragility.
2. **Complex Ad-Hoc Proration:** In accordance with standard recurring B2B subscriptions, billing is anchored to start dates and billed in advance, avoiding messy floating-point proration approximations.
3. **Client-Side SPA / Heavy JavaScript Frameworks:** Built entirely on server-rendered semantic HTML with the Counting House Ledger design system, plain POST-Redirect-GET forms, and zero client-side bundle bloat, ensuring sub-50ms page renders and complete predictability.
