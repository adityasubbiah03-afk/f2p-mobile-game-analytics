-- Daily active users, new installs and revenue
WITH dau AS (
  SELECT activity_date AS dt, COUNT(DISTINCT player_id) AS dau, SUM(sessions) AS sessions
  FROM daily_activity GROUP BY activity_date),
inst AS (SELECT install_date AS dt, COUNT(*) AS installs FROM players GROUP BY install_date),
rev AS (SELECT purchase_date AS dt, SUM(amount_usd) AS revenue, COUNT(DISTINCT player_id) AS payers
        FROM purchases GROUP BY purchase_date)
SELECT dau.dt, dau.dau, COALESCE(inst.installs,0) AS installs, dau.sessions,
       ROUND(1.0*dau.sessions/dau.dau, 2) AS sessions_per_dau,
       COALESCE(rev.revenue,0) AS revenue, COALESCE(rev.payers,0) AS paying_dau,
       ROUND(COALESCE(rev.revenue,0)/dau.dau, 4) AS arpdau
FROM dau LEFT JOIN inst USING(dt) LEFT JOIN rev USING(dt)
ORDER BY dau.dt;
