-- Two separate scoreboards (GAME_DESIGN.md, Scoring): the jagerslijst ranks
-- on self-finds + own-find help credit, the verzamelaarslijst on pluk
-- encounters + new people met + the bonded count. Apply once to existing
-- databases (ship BEFORE deploying the code that reads pluks.scored):
--   wrangler d1 execute foxhunt --local  --file=migrations/2026-08-13-two-scoreboards.sql
--   wrangler d1 execute foxhunt --remote --file=migrations/2026-08-13-two-scoreboards.sql

-- Whether this pluk row minted scoreboard weight when it was reported (it
-- passed the freshness check and the per-phase/total caps). The row itself
-- is the dedup ledger and is recorded either way; the scoreboard must not
-- re-derive the cap decision later, when more rows exist than did at grant
-- time.
ALTER TABLE pluks ADD COLUMN scored INTEGER NOT NULL DEFAULT 0;

-- Backfill from the event log: pluk_creature_found events carry granted=true
-- exactly when the report was fresh, under the caps and new to the roster.
UPDATE pluks
SET scored = 1
WHERE EXISTS (
  SELECT 1 FROM game_events
  WHERE game_events.type = 'pluk_creature_found'
    AND json_extract(game_events.payload, '$.player_id') = pluks.player_id
    AND json_extract(game_events.payload, '$.bssid') = pluks.bssid
    AND json_extract(game_events.payload, '$.phase') = pluks.phase
    AND json_extract(game_events.payload, '$.granted') = 1
);

-- Help credit now requires the giver to have the shared creature stamped
-- zelf gevonden (sharing an own find; resharing scores nothing). Drop credits
-- minted under the old any-eligible-share rule that the new rule would not
-- have granted.
DELETE FROM helped_players
WHERE NOT EXISTS (
  SELECT 1
  FROM creature_shares cs
  JOIN players_creatures pc
    ON pc.player_id = helped_players.giver_id
   AND pc.creature_id = cs.creature_id
  WHERE cs.id = helped_players.first_share_id
    AND pc.self_found = 1
);
