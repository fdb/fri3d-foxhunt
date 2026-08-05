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
  -- LoRa HID (spec §2.2): uint16 on the wire, allocated 1-9999. NULL until an antenna is attached.
  hunter_id INTEGER UNIQUE,
  badge_id TEXT NOT NULL UNIQUE, -- machine.unique_id() / base MAC
  name TEXT NOT NULL,
  profile_pic TEXT NOT NULL DEFAULT '',
  dt_created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  dt_updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  -- Soft delete (the badge's "alles wissen"). The row stays so an organiser
  -- can undo a regretted wipe, and so badge_id keeps its UNIQUE slot; a
  -- re-registration on this badge revives THIS row rather than adding a second.
  -- NULL = live. Every player-facing read filters on it.
  dt_deleted TEXT,
  -- How many creatures this player has fully bonded (band 5). Self-reported
  -- by the badge through the report outbox — display-only on the scoreboard,
  -- never the ranking key (GAME_DESIGN.md, "What bond buys").
  bonded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS players_creatures (
  player_id INTEGER NOT NULL REFERENCES players(id),
  creature_id INTEGER NOT NULL,
  dt_found TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (player_id, creature_id)
);

-- Snuffel reports: the badge reports a MEETING, never a catch
-- (GAME_DESIGN.md, "How a creature reaches the profile"). One row per
-- (player, peer, day) is the server-side rate limit on grants; vonk SCORE,
-- when it is built, will be computed by corroborating the pair's two rows —
-- and only inside the camp window (GAME_DESIGN.md, "Buiten het kamp").
CREATE TABLE IF NOT EXISTS snuffels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  peer TEXT NOT NULL, -- the other badge's MAC, as the report names it
  day TEXT NOT NULL, -- YYYY-MM-DD, the badge's snuffel day
  creature_id INTEGER, -- vonk-geluk outcome, NULL when none rolled
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, peer, day)
);

-- Successful wild-creature encounters while plukken. Food remains badge-local;
-- only the creature needs this durable record so account restore cannot lose it.
-- One success per physical AP and 15:00-to-15:00 camp phase is sufficient:
-- failed rolls are deterministic and cannot become a later success by retrying.
CREATE TABLE IF NOT EXISTS pluks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  bssid TEXT NOT NULL,
  phase TEXT NOT NULL, -- YYYY-MM-DD label of the phase's 15:00 start day
  creature_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, bssid, phase)
);
