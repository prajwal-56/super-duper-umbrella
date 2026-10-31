SELECT i.id,
       i.amount_paid_minor,
       i.total_minor,
       (SELECT COALESCE(SUM(amount_minor), 0) FROM payments p WHERE p.invoice_id = i.id) AS paid_sum,
       i.status
FROM invoices i
WHERE i.amount_paid_minor < 0
   OR i.amount_paid_minor > i.total_minor
   OR (i.status = 'paid' AND i.amount_paid_minor != i.total_minor)
   OR (i.status != 'paid' AND i.amount_paid_minor = i.total_minor);