WITH RECURSIVE
  all_subs AS (
    SELECT id, start_date, expiry_date, status, is_paused
    FROM subscriptions
    WHERE status IN ('active', 'closed')
  ),
  all_periods AS (
    SELECT
      id AS sub_id,
      start_date + (g.g || ' month')::interval AS period_start,
      LEAST(start_date + (g.g + 1 || ' month')::interval - INTERVAL '1 day', expiry_date) AS period_end
    FROM all_subs, generate_series(0, 35) AS g
    WHERE start_date + (g.g || ' month')::interval <= expiry_date
  ),
  invoiced AS (
    SELECT DISTINCT sub_id, period_start
    FROM invoices
    WHERE status <> 'cancelled'
  ),
  paused AS (
    SELECT DISTINCT sub_id, period_start
    FROM subscription_pauses
    WHERE is_paused = false
      OR (period_start >= paused_on AND (period_end IS NULL OR period_start < resumed_on))
  )
SELECT p.sub_id, p.period_start
FROM all_periods p
LEFT JOIN invoiced i ON p.sub_id = i.sub_id AND p.period_start = i.period_start
LEFT JOIN paused pa ON p.sub_id = pa.sub_id AND p.period_start = pa.period_start
WHERE i.sub_id IS NULL AND pa.sub_id IS NULL;