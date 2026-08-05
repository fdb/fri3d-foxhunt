-- Migration for databases created before 2026-08-05 (schema.sql creates all
-- of this on a fresh init; existing DBs need the deltas once):
--   wrangler d1 execute foxhunt --local  --file=migrations/2026-08-05-snuffels-and-bonded.sql
--   wrangler d1 execute foxhunt --remote --file=migrations/2026-08-05-snuffels-and-bonded.sql

ALTER TABLE players ADD COLUMN bonded INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS snuffels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  peer TEXT NOT NULL,
  day TEXT NOT NULL,
  creature_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, peer, day)
);
