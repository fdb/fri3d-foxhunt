# Foxhunt cloud server

Cloudflare Worker (Hono + D1 + HTMX) that keeps badge registrations and
scoring for the fox hunt. All game activity lands in the append-only
`game_events` log; `players` and `players_creatures` are projections of it.

## Routes

| Route                   | Method | Description                                                         |
| ----------------------- | ------ | ------------------------------------------------------------------- |
| `/api/v1/auth/register` | POST   | Register a badge: `{ badge_id, name, hunter_id? }`                  |
| `/api/v1/auth/user`     | GET    | Restore: look up an account by `?badge_id=...` (404 = new badge)   |
| `/api/v1/auth/user`     | PATCH  | Update account by `badge_id`: `{ name?, hunter_id?, profile_pic? }` |
| `/api/v1/player/found`  | POST   | Bridge relay reports `{ hunter_id, fox_id }` (Bearer `BRIDGE_KEY`)  |
| `/`                     | GET    | Public dashboard, auto-refreshing scoreboard                        |
| `/debug/log`            | GET    | Event log — HTML table, or JSON with `Accept: application/json`     |

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
