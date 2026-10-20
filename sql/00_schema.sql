-- Indexes + the Cookie-Cats-style A/B table, derived from raw events.
CREATE INDEX IF NOT EXISTS ix_da_player ON daily_activity(player_id, day_offset);
CREATE INDEX IF NOT EXISTS ix_da_date   ON daily_activity(activity_date);
CREATE INDEX IF NOT EXISTS ix_pu_player ON purchases(player_id);
CREATE INDEX IF NOT EXISTS ix_pu_date   ON purchases(purchase_date);

DROP VIEW IF EXISTS ab_test;
CREATE VIEW ab_test AS
SELECT p.player_id AS userid,
       p.version,
       COALESCE(SUM(CASE WHEN d.day_offset <= 13 THEN d.rounds END), 0) AS sum_gamerounds,
       MAX(CASE WHEN d.day_offset = 1 THEN 1 ELSE 0 END) AS retention_1,
       MAX(CASE WHEN d.day_offset = 7 THEN 1 ELSE 0 END) AS retention_7
FROM players p
LEFT JOIN daily_activity d ON d.player_id = p.player_id
GROUP BY p.player_id, p.version;
