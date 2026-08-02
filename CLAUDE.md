# Foxhunt — working notes

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

## Conventions
- **Never touch pins.** Use `mpos.*` managers (`mpos.lights`, `AudioManager`) and
  gate on availability — desktop has no LEDs and no buzzer output, so those calls
  must no-op and fall back (e.g. the on-screen LED mirror).
- **Artwork:** PNGs (with their Aseprite sources) live in `artwork/<folder>/` —
  `animals/` are the huntable creatures (16×16 RGBA), `companion/` the maatje,
  `title-screen/` the 320×120 welcome banner. `scripts/bake_sprites.sh` mirrors
  the PNGs (only) into `be.fri3d.foxhunt/assets/`, **keeping the folder
  structure**, so `artwork/animals/vos.png` → `assets/animals/vos.png`. Re-run
  it after changing artwork; `--check` reports drift. Both sides are committed,
  and every PNG under `assets/` belongs to the script (orphans get pruned).
  A creature opts into real art with an `"img"` field in `creatures.py` — the
  bare filename, `art.py` owns the folder; without it, it falls back to the
  procedural placeholder shape.
- **Don't name an asset dir after an imported module** — a folder `creatures/`
  shadows `creatures.py` on import. That's why creature art lives in
  `assets/animals/`.
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

## Layout source of truth
`layout/foxhunt-layout.html` is the pixel-exact 320×240 spec — it owns
sizes, gaps and colours; keep them in sync. *How* the app expresses them is in
`DESIGN.md`: repeated elements use LVGL flex via `ui.row(...)` (positions are
computed, not transcribed); only one-off panels keep absolute coords. Colours
and spacing are tokens in `ui.py`, applied through shared `lv.style_t` objects —
read `DESIGN.md` before adding a screen.
