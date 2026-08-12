-- Verified self-find provenance, corroborated directed snuffel shares and
-- first-help scoring. Apply once to existing databases:
--   wrangler d1 execute foxhunt --local  --file=migrations/2026-08-12-scoring-and-snuffel-reports.sql
--   wrangler d1 execute foxhunt --remote --file=migrations/2026-08-12-scoring-and-snuffel-reports.sql

ALTER TABLE players_creatures ADD COLUMN self_found INTEGER NOT NULL DEFAULT 0;
ALTER TABLE players_creatures ADD COLUMN dt_self_found TEXT;

-- Preserve verified finds made before provenance had its own columns.
UPDATE players_creatures
SET self_found = 1,
    dt_self_found = COALESCE(
      (
        SELECT MIN(game_events.created_at)
        FROM game_events
        WHERE game_events.type = 'fox_found'
          AND json_extract(game_events.payload, '$.player_id') = players_creatures.player_id
          AND json_extract(game_events.payload, '$.fox_id') = players_creatures.creature_id
      ),
      dt_found
    )
WHERE EXISTS (
  SELECT 1
  FROM game_events
  WHERE game_events.type = 'fox_found'
    AND json_extract(game_events.payload, '$.player_id') = players_creatures.player_id
    AND json_extract(game_events.payload, '$.fox_id') = players_creatures.creature_id
);

CREATE TABLE IF NOT EXISTS snuffel_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  encounter_id TEXT NOT NULL,
  peer TEXT NOT NULL,
  day TEXT NOT NULL,
  occurred_at INTEGER NOT NULL,
  had_vonk INTEGER NOT NULL,
  sent_creature_id INTEGER,
  received_creature_id INTEGER,
  received_was_new INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, encounter_id)
);

CREATE INDEX IF NOT EXISTS idx_snuffel_reports_match
ON snuffel_reports(encounter_id, player_id);

CREATE TABLE IF NOT EXISTS verified_sparks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  encounter_id TEXT NOT NULL UNIQUE,
  player_a INTEGER NOT NULL REFERENCES players(id),
  player_b INTEGER NOT NULL REFERENCES players(id),
  occurred_at INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_verified_sparks_pair
ON verified_sparks(player_a, player_b, occurred_at);

CREATE TABLE IF NOT EXISTS creature_shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  encounter_id TEXT NOT NULL,
  giver_id INTEGER NOT NULL REFERENCES players(id),
  recipient_id INTEGER NOT NULL REFERENCES players(id),
  creature_id INTEGER NOT NULL,
  occurred_at INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (encounter_id, giver_id, recipient_id, creature_id)
);

CREATE TABLE IF NOT EXISTS helped_players (
  giver_id INTEGER NOT NULL REFERENCES players(id),
  recipient_id INTEGER NOT NULL REFERENCES players(id),
  first_share_id INTEGER NOT NULL REFERENCES creature_shares(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (giver_id, recipient_id)
);
