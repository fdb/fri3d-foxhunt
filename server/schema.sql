-- Foxhunt cloud server schema (Cloudflare D1 / SQLite)

-- Append-only log of everything that happens in the game. The other tables
-- are projections that can be rebuilt from this log.
CREATE TABLE IF NOT EXISTS game_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  payload TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS players (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hunter_id INTEGER UNIQUE, -- LoRa id (0-9999), NULL until an antenna is attached
  badge_id TEXT NOT NULL UNIQUE, -- machine.unique_id() / base MAC
  name TEXT NOT NULL,
  profile_pic TEXT NOT NULL DEFAULT '',
  dt_created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  dt_updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS players_creatures (
  player_id INTEGER NOT NULL REFERENCES players(id),
  creature_id INTEGER NOT NULL,
  dt_found TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (player_id, creature_id)
);
