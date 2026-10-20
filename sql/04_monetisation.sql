-- ARPU / ARPPU / payer conversion by platform and A/B variant (first 30 days)
WITH rev AS (SELECT player_id, SUM(amount_usd) AS spend FROM purchases GROUP BY player_id)
SELECT p.platform, p.version,
       COUNT(*) AS players,
       SUM(rev.player_id IS NOT NULL) AS payers,
       ROUND(1.0*SUM(rev.player_id IS NOT NULL)/COUNT(*), 4) AS payer_conv,
       ROUND(COALESCE(SUM(rev.spend),0)/COUNT(*), 4) AS arpu,
       ROUND(COALESCE(SUM(rev.spend),0)/NULLIF(SUM(rev.player_id IS NOT NULL),0), 2) AS arppu
FROM players p LEFT JOIN rev USING(player_id)
GROUP BY p.platform, p.version ORDER BY p.platform, p.version;
