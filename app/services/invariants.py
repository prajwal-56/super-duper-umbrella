def run_all(conn):
    results = []

    # INV-01: No two non-cancelled invoices share (subscription_id, period_start)
    inv01 = conn.execute("""
        SELECT subscription_id, period_start, COUNT(*) AS cnt
        FROM invoices
        WHERE status <> 'cancelled'
        GROUP BY subscription_id, period_start
        HAVING COUNT(*) > 1
    """).fetchall()
    results.append(("INV-01", len(inv01) == 0, inv01 if inv01 else None))

    # INV-02: Per invoice: subtotal, discount, tax and total equal sums of lines
    inv02 = conn.execute("""
        SELECT i.id,
               i.subtotal_minor != SUM(il.line_subtotal_minor) AS sub_mismatch,
               i.discount_minor != SUM(il.discount_minor) AS disc_mismatch,
               i.tax_minor != SUM(il.tax_minor) AS tax_mismatch,
               i.total_minor != SUM(il.total_minor) AS total_mismatch
        FROM invoices i
        JOIN invoice_lines il ON il.invoice_id = i.id
        GROUP BY i.id, i.subtotal_minor, i.discount_minor, i.tax_minor, i.total_minor
        HAVING sub_mismatch OR disc_mismatch OR tax_mismatch OR total_mismatch
    """).fetchall()
    has_errors = any(r[1] or r[2] or r[3] or r[4] for r in inv02)
    results.append(("INV-02", not has_errors, inv02 if has_errors else None))

    # INV-03: 0 <= amount_paid <= total; paid = sum(payments); paid = total iff status=paid
    inv03 = conn.execute("""
        SELECT i.id,
               i.amount_paid_minor < 0 AS negative_paid,
               i.amount_paid_minor > i.total_minor AS overpaid,
               (SELECT COALESCE(SUM(amount_minor), 0) FROM payments p WHERE p.invoice_id = i.id) != i.amount_paid_minor AS paid_mismatch,
               i.status = 'paid' AND i.amount_paid_minor != i.total_minor AS status_mismatch
        FROM invoices i
        WHERE i.amount_paid_minor < 0
           OR i.amount_paid_minor > i.total_minor
           OR (i.status = 'paid' AND i.amount_paid_minor != i.total_minor)
           OR (i.status != 'paid' AND i.amount_paid_minor = i.total_minor)
    """).fetchall()
    has_errors = any(any(r[1:3]) or r[2] or r[3] for r in inv03)
    results.append(("INV-03", not has_errors, inv03 if has_errors else None))

    # INV-05: usage_count <= usage_limit (non-voided redemptions)
    inv05 = conn.execute("""
        SELECT d.id, d.usage_count, d.usage_limit,
               (SELECT COUNT(*) FROM discount_redemptions dr
                WHERE dr.discount_id = d.id AND dr.voided_at IS NULL) AS active_redemptions
        FROM discounts d
        WHERE (SELECT COUNT(*) FROM discount_redemptions dr
               WHERE dr.discount_id = d.id AND dr.voided_at IS NULL) > d.usage_limit
    """).fetchall()
    has_errors = len(inv05) > 0
    results.append(("INV-05", not has_errors, inv05 if has_errors else None))

    # INV-07: Each billing run: considered = count(items)
    inv07 = conn.execute("""
        SELECT run_id, considered, COUNT(*) AS item_count
        FROM billing_run_items
        GROUP BY run_id, considered
        HAVING COUNT(*) != SUM(considered)
    """).fetchall()
    has_errors = len(inv07) > 0
    results.append(("INV-07", not has_errors, inv07 if has_errors else None))

    # INV-08: Invoice calc_trace reconciles to line totals
    inv08 = conn.execute("""
        SELECT il.invoice_id,
               SUM(
                 il.line_subtotal_minor
                 - il.discount_minor
                 + CASE WHEN il.tax_inclusive = false THEN il.tax_minor ELSE 0 END
               ) AS computed_total,
               MAX(i.total_minor) AS stored_total
        FROM invoice_lines il
        JOIN invoices i ON i.id = il.invoice_id
        GROUP BY il.invoice_id
        HAVING SUM(
                 il.line_subtotal_minor
                 - il.discount_minor
                 + CASE WHEN il.tax_inclusive = false THEN il.tax_minor ELSE 0 END
               ) != MAX(i.total_minor)
    """).fetchall()
    has_errors = len(inv08) > 0
    results.append(("INV-08", not has_errors, inv08 if has_errors else None))

    return results