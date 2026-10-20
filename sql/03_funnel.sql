-- Player-journey funnel (first 14 days): install -> returned -> 4+ active days
-- -> reached 100+ rounds -> first purchase
WITH per AS (
  SELECT p.player_id,
         COUNT(DISTINCT CASE WHEN d.day_offset<=13 THEN d.day_offset END) AS active_days,
         COALESCE(SUM(CASE WHEN d.day_offset<=13 THEN d.rounds END),0) AS rounds14,
         MAX(d.day_offset=1) AS d1
  FROM players p LEFT JOIN daily_activity d USING(player_id) GROUP BY p.player_id),
buyers AS (SELECT DISTINCT player_id FROM purchases WHERE day_offset<=13)
SELECT step, players, ROUND(1.0*players/FIRST_VALUE(players) OVER (ORDER BY ord),4) AS pct_of_installs
FROM (
  SELECT 1 ord,'1 Installed' step, COUNT(*) players FROM per
  UNION ALL SELECT 2,'2 Returned within 14d', COUNT(*) FROM per WHERE active_days>=2
  UNION ALL SELECT 3,'3 Active 4+ days', COUNT(*) FROM per WHERE active_days>=4
  UNION ALL SELECT 4,'4 Reached 100+ rounds', COUNT(*) FROM per WHERE rounds14>=100
  UNION ALL SELECT 5,'5 Made a purchase', COUNT(*) FROM per JOIN buyers USING(player_id)
) ORDER BY ord;
