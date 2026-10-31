# DECISIONS — Brightloop Ledger

The build plan's decision register (§10), copied here as the working record.
New decisions are appended with the next number and a line in the owner's log.

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

## Additions

- **D-26 First admin and demo accounts:** the first admin is created at startup from `ADMIN_EMAIL`/`ADMIN_PASSWORD` when no admin exists (never overwrites). Signup always creates `role=customer` and ignores any submitted role field; staff are created only by an admin.
- **D-27 Session:** the session cookie is signed with `SECRET_KEY` (itsdangerous), httpOnly, SameSite=Lax, Secure when `APP_BASE_URL` is https, 14-day lifetime. It carries only the user id. State-changing requests check `Origin`/`Referer` against `APP_BASE_URL` when either header is present.
- **D-28 Reset tokens:** 32 random bytes, stored as SHA-256, 30-minute expiry, single-use; requesting a new token invalidates the old unused ones; the response is identical whether or not the address exists.
- **D-29 Root path:** `/` renders a small signed-in landing page while the staff dashboard (`/app`) is being built; after the dashboard lands, A may point `/` at it without changing login.
- **D-30 Where the IDOR tests live:** concrete IDOR assertions belong with the portal (A-11), the first customer-facing resource routes. On `main` today a customer has no id it can ask for, so an IDOR test would assert nothing; the route × role matrix (A-10) runs now over every registered route.
- **D-31 Template class contract:** the class names documented in `AGENTS.md` for `base.html` (`sheet`, `masthead`, `nav`, `whoami`, `system-date`, `content`, `folio`, `section`, `section-label`, `field`, `button`, `notice`, `errors`, `hint`, `small`, `link-button`, `form`, `logout-form`) are the layout contract and `ledger.css` must style them. C's component classes (`ledger-table`, `stamp`, `field__input`, ...) are used for content inside a section.
- **D-32 Outbox bodies are rendered:** `/app/outbox` shows `body_html` unescaped so the demo reads like an email. Every caller of `outbox.queue_email` must therefore build the body from escaped values (`html.escape` on any customer-supplied text); the stored link is the only clickable field the viewer adds itself.
