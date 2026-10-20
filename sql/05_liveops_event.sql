-- LiveOps weekend event vs the weekends either side.
-- Eligible = installed 3-30 days before each date (past D30 we stop observing players, and
-- brand-new installs behave differently). Install volume is flat, so tenure mix is identical
-- across the three weekends and the comparison is like-for-like.
WITH days(dt, label) AS (
  VALUES ('2026-08-15','Baseline (wk before)'),('2026-08-16','Baseline (wk before)'),
         ('2026-08-22','EVENT'),('2026-08-23','EVENT'),
         ('2026-08-29','Baseline (wk after)'),('2026-08-30','Baseline (wk after)')),
elig AS (SELECT dt, label, COUNT(*) AS eligible FROM days
         JOIN players p ON julianday(days.dt)-julianday(p.install_date) BETWEEN 3 AND 30
         GROUP BY dt, label),
act AS (SELECT d.activity_date AS dt, COUNT(DISTINCT d.player_id) AS active,
               SUM(d.coins_spent) AS coins_spent, SUM(d.coins_earned) AS coins_earned
        FROM daily_activity d WHERE d.day_offset>=3 AND d.activity_date IN (SELECT dt FROM days)
        GROUP BY d.activity_date),
rev AS (SELECT pu.purchase_date AS dt, SUM(amount_usd) AS revenue, COUNT(*) AS purchases
        FROM purchases pu WHERE pu.day_offset>=3 GROUP BY pu.purchase_date)
SELECT elig.label, elig.dt, elig.eligible, act.active,
       ROUND(1.0*act.active/elig.eligible,4) AS active_rate,
       COALESCE(rev.revenue,0) AS revenue,
       ROUND(COALESCE(rev.revenue,0)/elig.eligible,5) AS revenue_per_eligible,
       ROUND(1.0*act.coins_spent/act.coins_earned,3) AS sink_source_ratio
FROM elig JOIN act USING(dt) LEFT JOIN rev USING(dt) ORDER BY elig.dt;
