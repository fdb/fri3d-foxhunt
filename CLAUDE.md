# Vossenjacht — working notes

## Commit discipline
- **Commit after every meaningful, working change** — a fix or feature that builds
  and is verified on the emulator. Don't let verified work pile up uncommitted, and
  don't batch unrelated changes into one giant commit. Each commit should be one
  coherent step with a clear message.

## Run & verify (same source, both targets)
The identical app runs on the Fri3d 2026 badge and the macOS SDL emulator; the
board layer handles the hardware differences.
- The app is symlinked into a local MicroPythonOS checkout's `apps/`.
- Run: `cd /Users/fdb/Source/MicroPythonOS && ./scripts/run_desktop.sh be.fri3d.foxhunt`
- Headless smoke test: run it redirected to a log file and grep the log for
  `Traceback` / `Error`. Home rendering with no traceback means imports + that
  screen build cleanly (other screens build when navigated to).
- Full UI verification: pipe commands into the emulator's stdin REPL to
  simulate taps/drags/focus and capture screenshots — see
  `docs/emulator-testing.md`. Prefer this over "it should work" for any
  change with visible or interactive behaviour.
- **The emulator's profile is throwaway.** Whatever sits in
  `<MicroPythonOS>/internal_filesystem/data/be.fri3d.foxhunt/config.json` is
  test data — no real account, no real catches. Overwrite it with `{}` to
  replay first-run onboarding, or seed a profile to skip it, without asking.
  Only the badge and the server hold anything worth keeping.

## Deploying to the badge
`scripts/deploy_to_badge.sh [--start]` pushes the app over USB. Three things it
does that are not obvious, each because copying the files is not enough:
- **It copies only what differs, and deletes only what the source dropped.** The
  badge SHA-256s its whole app dir in one REPL trip; the script diffs that
  against the local files and hands `installapp` a stage holding just the
  changed ones (`mpremote fs cp -r` merges, so that updates exactly those).
  Both halves matter. mpremote never deletes, so a file that leaves the source
  stays forever — a renamed module, a superseded sprite folder, a stray
  `__pycache__` — until LittleFS is full and installs start truncating. And it
  hashes one file per REPL round trip, so letting it walk the full tree costs
  ~37s where the badge hashes all 71 itself in ~20s. Do *not* "simplify" this
  into wiping the app dir first: that guarantees every file is re-uploaded and
  takes a deploy from ~60s to ~215s. Save data is unaffected either way; it
  lives in `data/be.fri3d.foxhunt/`, not in the app dir.
- **It returns the badge to the launcher first**, so no live activity is holding
  the code being overwritten.
- **It drops the app's modules from `sys.modules`.** MicroPythonOS evicts only
  the *entrypoint* module between launches (`AppManager.execute_script`), so
  without this a relaunch runs the new `foxhunt.py` against the previous run's
  cached `screen_*` — new caller, stale callee. That mismatch is the exception
  you get from restarting a freshly-deployed app.

A deploy runs ~60s: ~20s of that is the badge hashing its files (dominated by
per-file `open()`, ~0.28s each — buffer size makes no difference), and the rest
is REPL round trips at ~4s of interpreter start and serial handshake apiece,
which is why the steps are folded into as few `exec` calls as possible.

The file count matters twice over: LittleFS bills a whole 4 KB block per file,
and each file costs ~0.28s of every deploy's hash pass. That is why the 40+
tiny sprite PNGs were folded into one `assets/sprites.bin` atlas (see
Conventions → Artwork) — reclaiming ~150 KB on device and ~12s per deploy.

End users never touch this path. The app store streams a `.mpk` over WiFi
straight into `AppManager.download_and_install_package`, which unzips it as it
downloads — seconds, not minutes. It `shutil.rmtree`s the app dir first, so a
store install is a clean replace and needs none of the above.

## Formatting
- `scripts/format.sh` formats all Python (Ruff via `uvx`) and JSON (stdlib
  `json.tool` via `uv`) — both Astral-runner-based, nothing installed into the
  project. `scripts/format.sh --check` reports unformatted files and exits 1 (CI).

## Glossary — one word per thing
The UI is Dutch, the code is English. Each concept has exactly one word on each
side; using the other side's word in the wrong place is how `mascot`/`maatje`
and two different "companions" happened.

| Code (English) | UI (Dutch) | What it is |
| --- | --- | --- |
| **companion** | **maatje** | The player's own avatar: a head + stacked accessories + a backdrop, built at registration. `companion.py`, `screen_companion.py`, `CompanionActivity`. |
| **creature** | **beest** | One of the huntable animals in the roster (`creatures.py`). Never a "companion". |
| **fox** | **vos** | A physical LoRa transmitter hidden in the field. The creature is what you *get*; the fox is what you *find*. |
| **hunter** | **jager** | The player, when playing with a LoRa antenna: has a minted `hunter_id`, shown as "JGR-04". |
| **collector** | **verzamelaar** | The player, when playing WiFi-only (no antenna): `hunter_id` is None. The UI shows the mode word where a jager would see their id. |
| **pet state** | — | The per-creature care stats — bond, hunger, mood (`pet.py`, `store.beast_state`). Belongs to a creature, never to the companion. |
| **shortcode** | — | The companion serialized for the wire: `H1A003C1` (`companion.encode` / `.decode`). |

Retired words: **mascot** (say companion), **mascotte** (say maatje) — except
as a citation of the original design bundle file `mascotte.jsx`.

## Conventions
- **Never touch pins.** Use `mpos.*` managers (`mpos.lights`, `AudioManager`) and
  gate on availability — desktop has no LEDs and no buzzer output, so those calls
  must no-op and fall back (e.g. the on-screen LED mirror).
- **Artwork:** PNGs (with their Aseprite sources) live in `artwork/<folder>/` —
  `animals/` are the huntable creatures (16×16 RGBA), `companions/` the maatje's
  heads and accessories (16×16 RGBA, one PNG per Aseprite layer, filename ==
  the id in `companion.py`), `title-screen/` the 320×120 welcome banner.
  `scripts/bake_sprites.sh` packs every 16px-tall PNG into ONE atlas —
  `assets/sprites.bin` (raw 16×16 BGRA frames, 1 KB each) plus the generated
  index `assets/atlas.py` — because on LittleFS forty tiny files cost 4 KB and
  ~0.28s of deploy each; other art (the title banner) is mirrored as PNG.
  Sprites keep their artwork-relative path as atlas key (`"animals/vos.png"`).
  Re-run the script after changing artwork; `--check` reports drift (CI). Both
  sides are committed, and everything the script generates belongs to it.
  A creature opts into real art with an `"img"` field in `creatures.py` — the
  bare filename, `art.py` owns the folder; without it, it falls back to the
  procedural placeholder shape.
- **Animated creatures:** a sprite that is a SHEET (width N×16, frames left to
  right, like `glitch_vos.png` at 80×16) bakes into N atlas frames
  automatically. Set `"anim": True` on the creature to play them — animation
  runs only where the payoff is honest (win/celebrate screens and the beast
  page pass `animate=True` to `art.creature_panel`); silhouettes, veils and
  grids hold frame 0. Playback is an `lv.anim_t` (`art.animate_sprite`), which
  LVGL kills with the widget — never an `lv.timer`, which would outlive it.
- **Don't name an asset dir after an imported module** — a folder `creatures/`
  shadows `creatures.py` on import. That's why creature art keys live under
  `animals/` and companion art under `companions/` (plural). The failure is
  silent and confusing: the import succeeds, then the module has no
  attributes.
- **Fonts** are 1-bit bitmap fonts in `assets/fonts/*.bin`, loaded with
  `lv.binfont_create`. Edit the source `.bdf` in `tools/bitmap_fonts/` (editor)
  and re-bake the deployed `.bin` with `scripts/bake_fonts.sh`
  (`--check` reports drift) — see `docs/fonts.md`. Coverage is ASCII 32–126
  ONLY: no `► ✓ · — é`. Substitute ASCII (`>`, `-`, "wel") or draw a pixel
  icon in `art.ICONS` (that's what the checkmark/cross/antenna icons are).
- **Back navigation** is the system left-edge swipe / Esc / joystick — apps don't
  draw their own back button.
- **LVGL native widgets have no `__dict__`** — you can't set Python attributes on
  them; keep per-widget state in the Activity.

## Cloud server
Base URL: **https://foxhunt.enigmeta.workers.dev/** — the badge's `registrar.py`
talks to `/api/v1/auth/*` there.

- **Test against a local worker, not prod.** `cd server && npm run dev` (plus
  `npm run db:init:local` once), then point the app at it from the emulator
  REPL before touching a screen:
  `import sys; sys.modules["registrar"].BASE_URL = "http://localhost:8787"`.
  The transport is drivable straight from the REPL, no UI needed —
  `sys.modules["registrar"].REGISTRAR.restore(badge, print)`.
- Only the **cloud** leg of `register()` is real. The bridge/hunter legs report
  `"skip"` because no LoRa bridge protocol exists yet (`fox_radio.py` is a stub
  too); a cloud save alone counts as success, which is the rule the flow
  already applied to an antenna-less badge.

- **Catches never flow badge → server.** That is an auth decision, not an
  unfinished wire: the only writer of `players_creatures` is
  `POST /api/v1/player/found`, held by the LoRa bridge behind a `BRIDGE_KEY`
  nobody else has. A badge that could report its own finds could report all of
  them. The badge *reads* its catch list back on restore
  (`GET /api/v1/auth/user` returns `creatures`) and never writes it.
  Consequence, accepted: a player with no antenna has `hunter_id = NULL`, so the
  bridge can't attribute their finds and a restore gives them back an account
  with no catches.
- The badge writes only what is its own to claim — name, `profile_pic`
  (companion shortcode), `hunter_id` — via register/PATCH.
- **Debug catches must never score.** Creatures "attained" through the debug
  screen (opened by tapping the badge id five times in settings) — the 1111
  test code, the roster toggles — land only in the badge's local store. The
  no-badge-writes rule above already guarantees they can't reach the
  scoreboard, but treat it as a requirement, not a happy accident: any future
  debug or test path must stay local-only and never produce a server-side
  catch.

## Server pages
`/` is the public one-pager (`components/Home.tsx`): what the game is, both
play tracks, screenshots. It renders through `<Layout bare>` — same `<head>`,
no green banner, no width cap, because it brings its own full-bleed sections.
The scoreboard lives at `/scores` and keeps the badge-flavoured `<Layout>`.

Its screenshots in `static/screens/` are 640×480 — an exact 2× of the badge's
320×240 screen — so they stay pixel-crisp at 320 or 640 CSS px, and
`image-rendering: pixelated` covers the sizes in between. Body copy is Nunito;
Pixelify Sans is for headings and the badge-mirroring UI (tables, buttons,
tags) only — it is unreadable at paragraph length.

## Server debug routes
`server/` (Hono on Cloudflare Workers + D1) exposes read-only inspection pages
under `/debug/*` — `/debug/log` for the event log, `/debug/players` for the
roster. Conventions for adding another one:
- **One handler, two representations.** Query D1 once, then
  `if (c.req.header("Accept")?.includes("application/json")) return c.json(...)`
  before falling through to the HTML render. Curl gets JSON, the browser gets a
  page — no separate `/api` twin.
- **Render through `<Layout>`** with a Dutch `title` and a `right` count badge
  (`` `${results.length} spelers` ``), and use the shared table markup:
  `class="muted"` for secondary columns, `<code>` for ids/hashes, and a
  `colspan` `class="empty"` row for the no-rows case.
- **Timestamps** go through the `shortTime` / `fullTime` helpers in
  `pages.tsx` — logs and lists show `YYYY-MM-DD HH:MM:SS`, the scoreboard just
  `HH:MM`. Never dump the raw ISO string in HTML; JSON keeps it verbatim.
- Debug pages are unauthenticated and unpolled — no HTMX refresh unless the page
  is meant to be left open (the scoreboard is the only one that is).

## Layout source of truth
`layout/foxhunt-layout.html` is the pixel-exact 320×240 spec — it owns
sizes, gaps and colours; keep them in sync. *How* the app expresses them is in
`DESIGN.md`: repeated elements use LVGL flex via `ui.row(...)` (positions are
computed, not transcribed); only one-off panels keep absolute coords. Colours
and spacing are tokens in `ui.py`, applied through shared `lv.style_t` objects —
read `DESIGN.md` before adding a screen.
