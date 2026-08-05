-- Durable pluk-creature encounters for databases created before 2026-08-06.
-- schema.sql creates this on a fresh database; existing databases need:
--   wrangler d1 execute foxhunt --local  --file=migrations/2026-08-06-pluks.sql
--   wrangler d1 execute foxhunt --remote --file=migrations/2026-08-06-pluks.sql

CREATE TABLE IF NOT EXISTS pluks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_id INTEGER NOT NULL REFERENCES players(id),
  bssid TEXT NOT NULL,
  phase TEXT NOT NULL,
  creature_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (player_id, bssid, phase)
);
