# Foxhunt — design & UI house rules

Two lenses, one goal: a consistent, legible, tactile little game that builds the
same on the Fri3d badge and the desktop emulator. The first lens is **LVGL done
idiomatically** (so the badge's limited RAM and the shared codebase stay happy);
the second is the **golden-age Apple HIG** principles the design already leans
on. Keep new screens scoring well on both.

The pixel spec is still `layout/foxhunt-layout.html` — it owns sizes, gaps,
and colours. This file owns *how we express them in code*.

---

## Design tokens (no magic values)

All of these live at the top of `ui.py`. Use the name, never the literal.

**Colour** — `INK PAPER CARD GREEN GREEN_D GOLD GOLD_D TERRA TERRA_D CREAM`
plus surfaces/semantics `SURFACE_SOFT SURFACE_TINT DORMANT TEXT_MUTED MYSTERY`.
If you reach for a raw `0x…` in a screen, it belongs in `ui.py` as a token first.
(`SURFACE_SOFT` 0xE9F1CF and `SURFACE_TINT` 0xEEF4D6 are near-duplicate pale
greens — a candidate to merge if we ever want one card surface.)

**Spacing / geometry** — `GAP_S(3) GAP_M(6) PAD(8) RADIUS(2) BORDER(2)
BORDER_THIN(1)`. Per-screen *background* colours and one-off coordinates from the
layout spec are allowed inline, but spacing between repeated things should be a
token or a `gap=` argument, not a fresh number.

**Fonts** — only `font_small()` / `font_label()` / `font_title()`. Three sizes is
the type scale; don't invent a fourth.

---

## LVGL rules

1. **Shared styles over inline.** Re-setting the same property on every widget
   grows that object's private local-style store. Define one `lv.style_t`
   (`_RESET`, `_PANEL`, `_SEG_CELL`, `_FOCUS`, `_PRESSED` in `ui.py`) and
   `add_style()` it. Reserve inline `set_style_*` for genuinely per-widget values
   (a specific bg colour, a one-off border colour). State-dependent looks
   (focus, pressed) belong in a style added with a state selector
   (`lv.PART.MAIN | lv.STATE.FOCUSED`), not four inline setters per widget.

2. **Flex for anything repeated; absolute only for one-offs.** If you're writing
   `x = base + i*(w+gap)`, use `ui.row(...)` (or `wrap=True` for a grid) and add
   children at `(0,0)` — LVGL places them. Give a wrap container a few px of
   slack so an exact-fit last column doesn't wrap early. Floating overlays inside
   a flex parent (speech bubble, favourite-food heart) use
   `LV_OBJ_FLAG_IGNORE_LAYOUT` and keep manual positions. One-off panels (banner,
   hunt scan card, win splash) stay absolute, read from named constants.

3. **Go through the `ui.py` helpers** — `make_screen / box / panel / label /
   row / seg_bar / heart_row / banner / focusable`. They carry the resets, tokens
   and shared styles. A screen that calls raw `lv.obj()` + a pile of setters is a
   smell.

4. **Mind the canvas cost.** Each sprite is an ARGB8888 `lv.canvas` buffer; a
   screen of them is real RAM. When refreshing in place, `clean()` the old
   subtree before rebuilding — see `HomeActivity.onResume` (don't re-run
   `setContentView`, it leaks the old screen + all its canvases).

5. **Never touch pins.** Hardware goes through `mpos.*` managers and must no-op +
   fall back on desktop (see CLAUDE.md).

---

## HIG principles (and how this app meets them)

- **Aesthetic integrity** — one coherent pixel-art world: integer sprite scales,
  the ink outline on every panel, baked bitmap fonts (no anti-alias). New art is
  16×16 RGBA; new scales are integer multiples.
- **Consistency** — same panel, same outline, same focus ring everywhere, because
  it all comes from the tokens + shared styles above. Change the look in one place.
- **Feedback** — every actionable widget gives a gold focus ring (joystick/arrow),
  a 2px press nudge (`_PRESSED`), *and* a sound. Don't add an action without all
  three. Inert items (dormant tiles) are focusable but give no press feedback.
- **Direct manipulation** — every tile/key/button is `focusable()` so the grid
  never goes dead; the catch *is* the reveal (silhouette → full art).
- **Forgiveness** — destructive/entry flows are reversible: the keypad has
  backspace; a wrong code clears and re-hides rather than punishing.
- **Deference** — content first, minimal chrome. No app-drawn back button — the
  system left-edge swipe / Esc / joystick owns back. Banners are thin.
- **Metaphor** — the Pokédex "boek", hearts for bond, a 5-LED hot/cold meter that
  mirrors the physical badge.

---

## Checklist for a new screen

- [ ] `ui.make_screen(<bg token>)`, build through `ui.*` helpers.
- [ ] Repeated elements in a `ui.row(...)`, not hand-computed coordinates.
- [ ] Colours/spacing are tokens; no new raw `0x…` or magic gaps in the screen.
- [ ] Every interactive element `ui.focusable(...)` with an `on_click` + a sound.
- [ ] No app-drawn back button.
- [ ] Sprites refresh via `clean()` + rebuild, never a second `setContentView`.
- [ ] Verified on the emulator against `layout/foxhunt-layout.html`.
