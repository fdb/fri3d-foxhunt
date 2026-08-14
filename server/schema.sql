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
  -- by the badge through the report outbox; bounds-checked and capped at the
  -- roster size. One of the three verzamelaarsscore components — it ranks on
  -- the verzamelaarslijst only, never on the jager board (GAME_DESIGN.md,
  -- Scoring).
  bonded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS players_creatures (
  player_id INTEGER NOT NULL REFERENCES players(id),
  creature_id INTEGER NOT NULL,
  dt_found TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  self_found INTEGER NOT NULL DEFAULT 0,
  dt_self_found TEXT,
  PRIMARY KEY (player_id, creature_id)
);

-- Legacy snuffel rows from the original one-sided reporting format. New badge
-- versions write snuffel_reports below so both sides can corroborate a spark.
CREATE TABLE IF NOT EXISTS snuffels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  peer TEXT NOT NULL, -- the other badge's MAC, as the report names it
  day TEXT NOT NULL, -- YYYY-MM-DD, the badge's snuffel day
  creature_id INTEGER, -- vonk-geluk outcome, NULL when none rolled
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, peer, day)
);

-- One report per badge for a shared ESP-NOW encounter. The matching report
-- from the peer corroborates directed creature introductions and help score.
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

-- First qualifying help, deduplicated per (giver, recipient). A row is minted
-- for a corroborated introduction of the giver's OWN find (self_found at
-- share time); the scoreboard follows first_share_id and applies the camp
-- window. Resharing spreads creatures but never lands here (GAME_DESIGN.md,
-- Scoring).
CREATE TABLE IF NOT EXISTS helped_players (
  giver_id INTEGER NOT NULL REFERENCES players(id),
  recipient_id INTEGER NOT NULL REFERENCES players(id),
  first_share_id INTEGER NOT NULL REFERENCES creature_shares(id),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (giver_id, recipient_id)
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
  -- 1 when this report minted scoreboard weight (fresh + under the caps) —
  -- the verzamelaarsscore counts these rows; over-cap or stale rows keep the
  -- dedup ledger honest without paying points.
  scored INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, bssid, phase)
);

-- Random visitor grants: a local badge schedule supplies at most three
-- fallback meetings. The server enforces slot dedupe and base-tier ids; debug
-- meetings never leave the badge and therefore never reach this table.
CREATE TABLE IF NOT EXISTS visitors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  slot INTEGER NOT NULL,
  creature_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, slot)
);
