WITH RECURSIVE
  all_subs AS (
    SELECT id, start_date, expiry_date
    FROM subscriptions
    WHERE status IN ('active', 'closed')
  ),
  all_periods AS (
    SELECT
      id AS sub_id,
      (start_date + (g.g || ' month')::interval)::date AS period_start,
      LEAST(start_date + (g.g + 1 || ' month')::interval - INTERVAL '1 day', expiry_date) AS period_end
    FROM all_subs, generate_series(0, 35) AS g
    WHERE start_date + (g.g || ' month')::interval <= expiry_date
  ),
  invoiced AS (
    SELECT DISTINCT sub_id, period_start
    FROM invoices
    WHERE status <> 'cancelled'
  ),
  paused_periods AS (
    SELECT DISTINCT sp.subscription_id AS sub_id, ap.period_start
    FROM subscription_pauses sp
    JOIN all_periods ap ON ap.sub_id = sp.subscription_id
    WHERE ap.period_start >= sp.paused_on
      AND (sp.resumed_on IS NULL OR ap.period_start < sp.resumed_on)
  )
SELECT p.sub_id, p.period_start
FROM all_periods p
LEFT JOIN invoiced i ON p.sub_id = i.sub_id AND p.period_start = i.period_start
LEFT JOIN paused_periods pa ON p.sub_id = pa.sub_id AND p.period_start = pa.period_start
WHERE i.sub_id IS NULL AND pa.sub_id IS NULL;
