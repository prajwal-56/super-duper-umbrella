# Tasks — C (catalog, subscriptions, UI system)

Legend: `- [ ] C-01 (45) ...` — rough minutes. Tier 0 unless marked.

## Prep (T+0:00, no dependencies)

- [ ] C-01 (45) Tier 0: `ledger.css` + `_ui.html` macros (§15) + `/styleguide` page showing every component. Push this FIRST; A needs it for `base.html`.

## After base-0a

- [ ] C-02 (50) Tier 0: catalog services and pages: taxes, payment terms, products (+ variants with extra price, notes), plans (interval, min quantity, availability, flags), plan price overrides, `resolve_unit_price`, `build_line_snapshot`.
- [ ] C-03 (15) Tier 0: customers list, create, edit (search, pagination).
- [ ] C-04 (25) Tier 0: quotation templates (plan, lines, validity).
- [ ] C-05 (60) Tier 0: `subscription_builder` (create manually or from template, line snapshots, min-quantity and plan-availability validation) and pages: list (filters by status, customer, plan; search; server-side pagination), new, detail (stepper from audit log, lines, invoices of this subscription, allowed-action buttons calling `lifecycle`, discount attach). Draft-only line editing.
- [ ] C-06 (30) Tier 0: discount rules admin (admin-only): kind, value, min purchase or quantity, dates, usage limit, scope and product; list and detail with usage count.
- [ ] C-07 (30) Tier 1: UI consistency pass across ALL pages in the hardening window (macros only, empty states, error states, print CSS).
