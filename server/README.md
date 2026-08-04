# Vossenjacht cloud server

Cloudflare Worker (Hono + D1 + HTMX) that keeps badge registrations and
scoring for the fox hunt. All game activity lands in the append-only
`game_events` log; `players` and `players_creatures` are projections of it.

Deployed at **https://foxhunt.enigmeta.workers.dev/** — the badge points
`registrar.py` at that host.

## Trust model

**A badge can never report its own finds.** The single writer of
`players_creatures` is `POST /api/v1/player/found`, and it is held by the LoRa
bridge behind a pre-shared `BRIDGE_KEY`. That key is the anti-cheat: finding a
fox means having been within radio range of it, and the bridge is the only
thing that can vouch for that. A badge-facing write route would let anyone
`curl` themselves a full dossier.

So the badge's traffic is asymmetric, on purpose:

- **writes** only what is its own to claim — `name`, `profile_pic`, `hunter_id`
  — through register and PATCH;
- **reads** its catch list back on restore, because `players_creatures` is the
  only copy that survives a wiped badge.

The accepted cost: a player with no antenna has `hunter_id = NULL`, the bridge
can't attribute their finds, and a restore hands them back an account with no
catches.

## Routes

| Route                   | Method | Description                                                         |
| ----------------------- | ------ | ------------------------------------------------------------------- |
| `/api/v1/auth/register` | POST   | Register a badge: `{ badge_id, name, hunter_id?, profile_pic? }`    |
| `/api/v1/auth/user`     | GET    | Restore by `?badge_id=...`: account + `creatures` (404 = new badge) |
| `/api/v1/auth/user`     | PATCH  | Update account by `badge_id`: `{ name?, hunter_id?, profile_pic? }` |
| `/api/v1/player/found`  | POST   | Bridge relay reports `{ hunter_id, fox_id }` (Bearer `BRIDGE_KEY`)  |
| `/`                     | GET    | Public landing page: what the game is, both play tracks             |
| `/scores`               | GET    | Public dashboard, auto-refreshing scoreboard                        |
| `/debug/log`            | GET    | Event log — HTML table, or JSON with `Accept: application/json`     |

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

## Deployment

```sh
wrangler d1 create foxhunt        # paste the id into wrangler.toml
npm run db:init:remote
wrangler secret put BRIDGE_KEY
npm run deploy
```
