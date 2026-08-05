# Vossenjacht cloud server

Cloudflare Worker (Hono + D1 + HTMX) that keeps badge registrations and
scoring for the fox hunt. All game activity lands in the append-only
`game_events` log; `players` and `players_creatures` are projections of it.

Deployed at **https://foxhunt.enigmeta.workers.dev/** — the badge points
`registrar.py` at that host.

## Trust model

**A badge can never report its own LoRa find.** `POST /api/v1/player/found` is
held by the LoRa bridge behind a pre-shared `BRIDGE_KEY`. That key is the
anti-cheat: finding a fox means having been within radio range of it, and the
bridge is the only thing that can vouch for that.

Other acquisition tracks deliberately have narrow badge-facing reports:
snuffelen reports a meeting; plukken reports a seeded BSSID/camp-phase wild
encounter. They make permanent collection progress restorable, but never mint
`zelf gevonden` provenance or hunter score. Forging them is bounded personal
collection modification, not a forged radio achievement.

So the badge's traffic is asymmetric, on purpose:

- **writes** what is its own to claim — profile fields, care summaries,
  meetings and wild pluk encounters;
- **reads** its catch list back on restore, because `players_creatures` is the
  only copy that survives a wiped badge.

## Routes

| Route                   | Method | Description                                                         |
| ----------------------- | ------ | ------------------------------------------------------------------- |
| `/api/v1/auth/register` | POST   | Register a badge: `{ badge_id, name, hunter_id?, profile_pic? }`    |
| `/api/v1/auth/user`     | GET    | Restore by `?badge_id=...`: account + `creatures` (404 = new badge) |
| `/api/v1/auth/user`     | PATCH  | Update account by `badge_id`: `{ name?, hunter_id?, profile_pic? }` |
| `/api/v1/auth/user`     | DELETE | Wipe the account: `{ badge_id }` — see "Wiping an account"          |
| `/api/v1/player/found`  | POST   | Bridge relay reports `{ hunter_id, fox_id }` (Bearer `BRIDGE_KEY`)  |
| `/api/v1/player/snuffel`| POST   | Badge reports a meeting and optional spreadable creature grant     |
| `/api/v1/player/pluk`   | POST   | Badge reports `{ bssid, phase, creature_id }` wild encounter       |
| `/`                     | GET    | Public landing page: what the game is, both play tracks             |
| `/scores`               | GET    | Public dashboard, auto-refreshing scoreboard                        |
| `/debug/log`            | GET    | Event log — HTML table, or JSON with `Accept: application/json`     |

### `fox_id` is the creature id, not the FID byte

`/found` is plain JSON, so `fox_id` is just a number — but it is `CHAR`, the
creature's character code (0-31), which on the air is only the **5 MSB** of the
FID byte (LoRa spec §2.1; the 3 LSB are `SEQ`, the TDMA slot). A relay holding a
FID must send `FID >> 3`.

Worth stating because getting it wrong is quiet: for `CHAR` 0-3 the raw FID is
still ≤ 31, so it passes validation and credits the **wrong creature**. Only
`CHAR` ≥ 4 pushes the byte past 31 and earns a 400.

## Wiping an account

`badge_id` is the MAC and never changes, so a badge cannot start over on its
own: wipe it locally and the next registration hits the 409 fork, adopts the
same account and hands every catch back. `DELETE /api/v1/auth/user` is what
makes the badge's "ALLES WISSEN" true — for a badge changing hands, and for a
player who wants their name off the public scoreboard.

The delete is **soft**. `players.dt_deleted` is stamped; the row stays.

- Invisible everywhere a player looks: restore 404s, PATCH 404s, `/found`
  refuses (so a stale HID the bridge still holds cannot resurrect it), and
  `/scores` drops it.
- Still listed on `/debug/players`, tagged **gewist** — that page is where an
  organiser undoes a regretted wipe (`UPDATE players SET dt_deleted = NULL`).
- Idempotent: a second delete returns `{ ok: true, already: true }`, so a badge
  that lost the response and retried never sees an error it has to explain.
- Registering again on the badge **revives that row** rather than adding a
  second: name and maatje are the new ones, `hunter_id` is cleared and
  `players_creatures` is emptied, so the next player starts genuinely empty
  with their own startbeest.

Two limits, both deliberate:

- **This is not erasure.** `game_events` is append-only and the other tables are
  projections of it, so the original `player_registered` still carries the name.
  The delete removes the account from the game and from the public site.
- **It is unauthenticated**, like every other route here. Soft is the mitigation:
  a `PATCH` can already rename any account whose MAC you can see, but that is
  repairable, and a hard delete of a catch list would not be — those creatures
  only come back by walking to the foxes again.

`scripts/test_server_wipe.sh` walks the whole lifecycle against a local worker.

## The companion shortcode (`profile_pic`)

The badge's avatar is stored as an 8-character code, `H1A003C1`:

| Part   | Meaning                                                      |
| ------ | ------------------------------------------------------------ |
| `H1`   | head — 1-based index into the badge's head roster            |
| `A003` | accessories — 12-bit bitmask, three **hex** digits           |
| `C1`   | backdrop colour — 1-based index into the badge's swatch list |

`be.fri3d.foxhunt/assets/companion.py` owns the format (`encode` / `decode`); the
server only validates the shape and stores it. Indices are 1-based so `0` can
never read as "unset", and the badge degrades unknown indices to its default
companion rather than refusing them — that keeps an older badge able to restore an
account minted by a newer roster.

## Development

```sh
npm install
cp .dev.vars.example .dev.vars
npm run db:init:local
npm run dev
```

`schema.sql` is all `CREATE TABLE IF NOT EXISTS`, so it never alters a table
that already exists. A database created before a column was added needs the
matching file from `migrations/` run once:

```sh
wrangler d1 execute foxhunt --local  --file=migrations/001_soft_delete.sql
wrangler d1 execute foxhunt --remote --file=migrations/001_soft_delete.sql
wrangler d1 execute foxhunt --local  --file=migrations/2026-08-05-snuffels-and-bonded.sql
wrangler d1 execute foxhunt --remote --file=migrations/2026-08-05-snuffels-and-bonded.sql
wrangler d1 execute foxhunt --local  --file=migrations/2026-08-06-pluks.sql
wrangler d1 execute foxhunt --remote --file=migrations/2026-08-06-pluks.sql
```

## Deployment

```sh
wrangler d1 create foxhunt        # paste the id into wrangler.toml
npm run db:init:remote
wrangler secret put BRIDGE_KEY
npm run deploy
```
