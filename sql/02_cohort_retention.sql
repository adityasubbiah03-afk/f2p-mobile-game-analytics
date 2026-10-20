-- Weekly install-cohort retention at D1 / D7 / D14 / D30
SELECT strftime('%Y-%W', p.install_date) AS cohort_week,
       COUNT(*) AS installs,
       ROUND(AVG(d1.player_id IS NOT NULL), 4)  AS d1,
       ROUND(AVG(d7.player_id IS NOT NULL), 4)  AS d7,
       ROUND(AVG(d14.player_id IS NOT NULL), 4) AS d14,
       ROUND(AVG(d30.player_id IS NOT NULL), 4) AS d30
FROM players p
LEFT JOIN daily_activity d1  ON d1.player_id=p.player_id  AND d1.day_offset=1
LEFT JOIN daily_activity d7  ON d7.player_id=p.player_id  AND d7.day_offset=7
LEFT JOIN daily_activity d14 ON d14.player_id=p.player_id AND d14.day_offset=14
LEFT JOIN daily_activity d30 ON d30.player_id=p.player_id AND d30.day_offset=30
GROUP BY cohort_week ORDER BY cohort_week;
