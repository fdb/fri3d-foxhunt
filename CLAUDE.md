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
| **hunter** | **jager** | The player. |
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
  the id in `companion.py`), `title-screen/` the 320×120 welcome banner. `scripts/bake_sprites.sh` mirrors
  the PNGs (only) into `be.fri3d.foxhunt/assets/`, **keeping the folder
  structure**, so `artwork/animals/vos.png` → `assets/animals/vos.png`. Re-run
  it after changing artwork; `--check` reports drift. Both sides are committed,
  and every PNG under `assets/` belongs to the script (orphans get pruned).
  A creature opts into real art with an `"img"` field in `creatures.py` — the
  bare filename, `art.py` owns the folder; without it, it falls back to the
  procedural placeholder shape.
- **Don't name an asset dir after an imported module** — a folder `creatures/`
  shadows `creatures.py` on import. That's why creature art lives in
  `assets/animals/` and companion art in `assets/companions/` (plural). The
  failure is silent and confusing: the import succeeds, then the module has no
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
