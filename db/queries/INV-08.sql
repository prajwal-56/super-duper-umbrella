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
       ) != MAX(i.total_minor);