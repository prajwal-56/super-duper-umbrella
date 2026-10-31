SELECT considered, COUNT(*) AS item_count
FROM billing_run_items
GROUP BY considered
HAVING COUNT(*) != SUM(considered);