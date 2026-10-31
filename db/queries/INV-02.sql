SELECT i.id,
       i.subtotal_minor AS line_subtotal,
       SUM(il.line_subtotal_minor) AS line_subtotal_sum,
       i.discount_minor AS line_discount,
       SUM(il.discount_minor) AS line_discount_sum,
       i.tax_minor AS line_tax,
       SUM(il.tax_minor) AS line_tax_sum,
       i.total_minor AS line_total,
       SUM(il.total_minor) AS line_total_sum
FROM invoices i
JOIN invoice_lines il ON il.invoice_id = i.id
GROUP BY i.id, i.subtotal_minor, i.discount_minor, i.tax_minor, i.total_minor
HAVING i.subtotal_minor != SUM(il.line_subtotal_minor)
   OR i.discount_minor != SUM(il.discount_minor)
   OR i.tax_minor != SUM(il.tax_minor)
   OR i.total_minor != SUM(il.total_minor);