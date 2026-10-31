WITH raw AS (
    SELECT
        COUNT(*) FILTER (WHERE status = 'active') AS active_count,
        COALESCE(SUM(amount_paid_minor), 0) AS collected,
        COALESCE(SUM(total_minor - amount_paid_minor), 0) AS outstanding
    FROM invoices
),
overdue AS (
    SELECT
        COUNT(*) FILTER (WHERE status = 'confirmed' AND total_minor > amount_paid_minor AND due_date < %s) AS overdue_count,
        COALESCE(SUM(CASE WHEN status = 'confirmed' AND total_minor > amount_paid_minor AND due_date < %s THEN total_minor - amount_paid_minor END), 0) AS overdue_amount
    FROM invoices
)
SELECT r.active_count, r.collected, r.outstanding, o.overdue_count, o.overdue_amount
FROM raw r, overdue o;
