-- Recover first-help facts discarded by the one-week-early camp window.
-- Apply once to existing databases before deploying the corrected worker:
--   wrangler d1 execute foxhunt --local  --file=migrations/2026-08-14-score-window-repair.sql
--   wrangler d1 execute foxhunt --remote --file=migrations/2026-08-14-score-window-repair.sql
--
-- creature_shares already contains only corroborated, eligible introductions
-- that were new to the recipient. A help additionally requires the giver's
-- own-find stamp to predate the share. Rank those immutable facts so the first
-- qualifying introduction wins globally; /scores applies the camp window to
-- that first_share_id. INSERT OR IGNORE makes this safe to retry.

WITH eligible_help AS (
  SELECT
    cs.giver_id,
    cs.recipient_id,
    cs.id AS first_share_id,
    ROW_NUMBER() OVER (
      PARTITION BY cs.giver_id, cs.recipient_id
      ORDER BY cs.occurred_at, cs.id
    ) AS pair_rank
  FROM creature_shares cs
  JOIN players_creatures pc
    ON pc.player_id = cs.giver_id
   AND pc.creature_id = cs.creature_id
  WHERE pc.self_found = 1
    AND unixepoch(pc.dt_self_found) <= cs.occurred_at
)
INSERT OR IGNORE INTO helped_players
  (giver_id, recipient_id, first_share_id)
SELECT giver_id, recipient_id, first_share_id
FROM eligible_help
WHERE pair_rank = 1;
