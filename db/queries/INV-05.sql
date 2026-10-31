SELECT d.id, d.usage_count, d.usage_limit,
       (SELECT COUNT(*) FROM discount_redemptions dr
        WHERE dr.discount_id = d.id
          AND dr.voided_at IS NULL) AS active_redemptions
FROM discounts d
WHERE d.usage_count < d.usage_limit
  AND (SELECT COUNT(*) FROM discount_redemptions dr
       WHERE dr.discount_id = d.id AND dr.voided_at IS NULL) > d.usage_limit;