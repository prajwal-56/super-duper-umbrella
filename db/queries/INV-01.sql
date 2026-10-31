SELECT subscription_id, period_start, COUNT(*) AS cnt
FROM invoices
WHERE status <> 'cancelled'
GROUP BY subscription_id, period_start
HAVING COUNT(*) > 1;