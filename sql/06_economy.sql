-- Soft-currency sink/source balance by player tenure (day since install)
SELECT day_offset, COUNT(*) AS active_player_days,
       SUM(coins_earned) AS earned, SUM(coins_spent) AS spent,
       ROUND(1.0*SUM(coins_spent)/SUM(coins_earned),3) AS sink_source_ratio,
       SUM(coins_earned)-SUM(coins_spent) AS net_coins_added
FROM daily_activity GROUP BY day_offset ORDER BY day_offset;
