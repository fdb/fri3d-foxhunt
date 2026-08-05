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
  `<MicroPythonOS>/internal_filesystem/prefs/be.fri3d.foxhunt/config.json` is
  test data — no real account, no real catches. Overwrite it with `{}` to
  replay first-run onboarding, or seed a profile to skip it, without asking.
  Only the badge and the server hold anything worth keeping.

## Deploying to the badge
`scripts/deploy_to_badge.sh [--start]` pushes the app over USB — ~8s when
nothing changed, ~15-20s for a typical change. Six things it does that are
not obvious, each because copying the files is not enough:
- **It refuses to silently replace another checkout's build.** More than one
  clone of this repo exists, and each clone's script would truthfully report
  "up to date" against its own tree while the developer believes they are
  testing the other one. Every install stamps `#src <dir> <commit> <dirty>`
  into the manifest; a deploy from a different directory than the badge's
  stamp refuses without `--force`, and every run prints both identities.
  A dirty working tree also refuses without `--force`: the settings screen
  shows `version @ commit` from that stamp (`screen_settings._build_info`),
  and a dirty deploy would make that sha a lie ('dev' when running from
  source, `*` after the sha when force-deployed dirty).
- **It ships `.mpy` bytecode, not source.** The badge spends ~2s of every
  cold start compiling 5k lines of Python; the in-tree mpy-cross (same
  checkout as the firmware, so the bytecode versions match) does it once at
  deploy time instead. `-march=xtensawin` so viper modules (`art_fast.py`)
  carry native code; `-O2`, not the OS's `-O3`, because O3's only extra
  saving is the line-number table and badge tracebacks need it. The emulator
  is untouched — its symlink runs the `.py` source directly.
- **It rides mpremote's raw REPL, never the aioREPL controller.** The aioREPL
  (`mpos_controller.py`) echoes every pasted byte back while LVGL starves the
  reader — ~115 B/s measured, and a payload past ~2.5KB stalls its flow
  control and dies on a write timeout. Raw REPL has no echo: the same state
  walk costs 16s through the controller and under 4 directly. The OS keeps
  running across raw-REPL execs (same interpreter — AppManager and
  `sys.modules` included), so the controller's emulator/testing workflow is
  untouched; it is just the wrong transport for deploy traffic. Relatedly:
  the controller's `read_until` must accept CRLF sentinel endings (fixed in
  the MicroPythonOS checkout) — before that, every serial exec silently sat
  out a 30s timeout and *then* returned the right answer, which made deploys
  7 minutes without a single error anywhere.
- **It trusts a shipped manifest instead of re-hashing.** Every install lands
  `.deploy.sha` ("sha16 size path" per line) inside the app dir; the next
  deploy stat-walks the tree and trusts the manifest only if the paths and
  every size match exactly, else falls back to hashing every file
  (~0.28s/file of `open()` overhead). Every way the manifest can lie is
  covered by that check or by placement: a truncated install (size differs),
  a lingering orphan (path extra), a store install (`rmtree` takes the
  manifest with it). Wrong → one slow hash pass, then it self-heals.
  The install itself is verified the same way, on-badge, before success is
  reported: path set + size against the just-pushed manifest, plus a full
  SHA-256 of exactly the files this run copied — because `fs cp` exiting 0
  is a transport claim, not proof the flash holds the bytes (a torn write
  once left a 0-byte `.mpy` behind a clean exit and a count-only "verify").
  On mismatch the badge drops its own manifest and the deploy fails loudly.
- **It copies only what differs, and deletes only what the source dropped.**
  `mpremote fs cp -r` merges, so a delta tree updates exactly the changed
  files; orphans are deleted explicitly (nothing on this path ever deletes
  on its own — a renamed module or stray `__pycache__` stays forever until
  LittleFS is full and installs start truncating). It returns the badge to
  the launcher first, so no live activity holds the code being overwritten.
  Save data is unaffected either way; it lives in `data/be.fri3d.foxhunt/`,
  not in the app dir.
- **It drops the app's modules from `sys.modules`.** MicroPythonOS evicts only
  the *entrypoint* module between launches (`AppManager.execute_script`), so
  without this a relaunch runs the new `foxhunt.py` against the previous run's
  cached `screen_*` — new caller, stale callee. That mismatch is the exception
  you get from restarting a freshly-deployed app.

Every phase prints `[t+Ns]` elapsed time. Diagnose any slowdown against those
numbers first — the pipeline's costs live where nothing errors (handshakes,
echo, on-badge walks), so a regression is otherwise invisible.

The file count still matters twice over: LittleFS bills a whole 4 KB block per
file, and each file costs ~0.28s whenever the manifest is distrusted and the
hash fallback runs. That is why the 40+ tiny sprite PNGs were folded into one
`assets/sprites.bin` atlas (see Conventions → Artwork) — reclaiming ~96 KB of
blocks on device and shrinking the worst-case hash pass.

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
| **hunter** | **jager** | The player, when playing with a LoRa antenna: has a minted `hunter_id` (1-9999), shown as "JGR-0042". |
| **collector** | **verzamelaar** | The player, when playing WiFi-only (no antenna): `hunter_id` is None. The UI shows the mode word where a jager would see their id. |
| **pet state** | — | The per-creature care stats — bond, energy, hunger (`pet.py`, `store.beast_state`). Belongs to a creature, never to the companion. |
| **shortcode** | — | The companion serialized for the wire: `H1A003C1` (`companion.encode` / `.decode`). |

Retired words: **mascot** (say companion), **mascotte** (say maatje) — except
as a citation of the original design bundle file `mascotte.jsx`.

## Conventions
- **`telemetry.py`: nothing to see here.** It is deliberately misnamed. Leave
  it alone — don't rename it, don't "fix" it, don't flag it in reviews.
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
- **Never let LVGL scale a sprite.** Its software transform steps the source
  edge-to-edge in `(dest_w - 1)` increments (`lv_draw_sw_transform.c`), so any
  draw-time scaling — `set_scale`, inner-align STRETCH on a mismatched size —
  renders half-width edge pixels and stray double-width columns even at exact
  integer factors, on badge and desktop alike. `art.sprite_img` pre-scales by
  integer pixel replication instead, so the buffer already matches the widget
  and the transform never runs; keep every sprite on that path.
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
- **A second registration on a known badge is a question, not a policy.**
  `badge_id` is the MAC, so a 409 from `/register` means this *hardware* already
  has an account: the same player after a wipe, or a badge that changed hands.
  Those want opposite things and the badge cannot tell them apart, so the flow
  stops and shows the account it found (`screen_reg_send._build_exists`) — DAT
  BEN IK adopts it, OVERSCHRIJF PATCHes the new name and maatje onto it. Either
  answer keeps the `hunter_id` and the catch list: both are keyed to the badge,
  and there is no second account to move them to. `registrar.adopt` does the
  writing for both, and for the welcome screen's "herstel" — one definition of
  what recovery means. Do not restore the silent PATCH this replaced: it renamed
  a stranger's account without asking, and because nothing read the existing row
  back it left the badge with `hunter_id = None` and an empty roster while the
  server still held both, under a screen that said "je bent ingeschreven".
- **`hunter_id` is allocated 1-9999, four digits, even though the wire is wider.**
  The LoRa spec (§2.2) makes HID a big-endian `uint16` — `HID_hi`, `HID_lo`,
  1-65535, 0 reserved. We deliberately hand out only the bottom 1-9999 of that
  field: a camp brings hundreds of badges, so four digits is ~16x headroom, and
  a fixed-width id keeps "JGR-0042" the same size on every screen that prints it
  (home, profiel, instellingen, registratie).
  Two halves, and both matter:
  - **This is a rule for the allocator, not just the validator.** Whoever mints
    HIDs — the central node, at registration (§2.2) — must draw from 1-9999.
    Allocate randomly across the full 16 bits and ~85% of hunters get an id this
    server rejects with `400 invalid hunter_id`.
  - **Anything parsing the air still reads a full `uint16`.** We narrowed the
    allocation, never the field. Do not "optimise" a decoder down to 14 bits.
  Do NOT copy the 0-31 that `fox_id` uses. That range is not a hunter range: it
  is `CHAR`, the 5 MSB of the FID byte (§2.1) — the creature's character code,
  which is why 0-31 is exactly right for `fox_id` and was a bug for `hunter_id`.
  Never accept `0`: the spec reserves it, and every screen reads
  `hunter_id or "Verzamelaar"`, so a falsy id silently renders a jager as a
  collector.
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
`image-rendering: pixelated` covers the sizes in between.

**The roster is a spoiler; the public site must not hold it.** Every creature
ships as a flat `#86ad64` silhouette — the title banner's own green, alpha kept,
colour discarded — under `static/art/silhouettes/NN.png`. Numbered, not named: a
filename in view-source gives the roster away exactly as well as a picture
does. The Vos is no exception: it may be the favicon, but one full-colour
animal in a parade of shapes reads as a rendering fault, not as a hint. The
favicon and the nav brand keep their own copy at `static/vos.png`.
Never copy `artwork/animals/` into `server/static/` again. Body copy is Nunito;
Pixelify Sans is for headings and the badge-mirroring UI (tables, buttons,
tags) only — it is unreadable at paragraph length.

**The scoreboard says HOW MANY, never WHICH.** `/scores` is public, so it shows
each player's maatje, their catch count and when they last scored — and no
creature name, id or picture. `fetchScores` is written so it cannot leak one:
it counts `players_creatures` and never selects a `creature_id`. The names
belong to the badge that earned them and to `/debug/players/:id`.

## Server debug routes
`server/` (Hono on Cloudflare Workers + D1) exposes read-only inspection pages
under `/debug/*` — `/debug/log` for the event log, `/debug/players` for the
player list, `/debug/players/:id` for one player (maatje, account fields, catch
list with names, and the events that wrote them). Conventions for adding
another one:
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
- **Roster names live in the worker, never in `static/`.** `lib/creatures.ts`
  carries id → naam → tier so a debug page can say "Eend" instead of "7"; it is
  a port of `creatures.py`, names and tiers only. The spoiler rule above is
  about what the *public* site hands out, and a debug route nobody links is not
  that — but the art stays out of `static/` either way.
- **The maatje renders from the shortcode**, through `lib/companion.ts` (a port
  of `companion.py`: HEADS, ACCS, BGS and `decode`) and `<Companion>`, which
  stacks one `<img>` per layer exactly as `companion.draw()` stacks LVGL
  layers. Three things must stay in sync with the badge or the same shortcode
  draws two different maatjes: head order, ACCS order (it is both the bit
  positions *and* the draw order, append-only), and the BGS palette.
  The layer PNGs are inlined as data URIs by `scripts/bake_server_art.sh` into
  `lib/companion-art.ts` — not copied into `static/`, because a `konijn.png` in
  view-source leaks a roster name, and because an avatar is up to eleven layers
  and a list draws one per row. All fifteen are 2.7 KB. Re-run the script after
  changing `artwork/companions/`; `--check` reports drift. It is in
  `.prettierignore`: prettier would wrap the data URIs and the script owns the
  file's shape.
- **Sprite sizes must stay integer multiples of 16.** `image-rendering:
  pixelated` only keeps pixels square at whole scale factors. `.maatje` carries
  no border or padding — the backdrop is its own edge — and anything added
  later must sit OUTSIDE the box (`box-sizing: content-box`), because the
  global `border-box` takes it out of the art instead: a 2px frame turns a 96px
  avatar into a 5.75x scale. Same rule as the badge's "never let LVGL scale a
  sprite", same reason.

## Layout source of truth
`layout/foxhunt-layout.html` is the pixel-exact 320×240 spec — it owns
sizes, gaps and colours; keep them in sync. *How* the app expresses them is in
`DESIGN.md`: repeated elements use LVGL flex via `ui.row(...)` (positions are
computed, not transcribed); only one-off panels keep absolute coords. Colours
and spacing are tokens in `ui.py`, applied through shared `lv.style_t` objects —
read `DESIGN.md` before adding a screen.
