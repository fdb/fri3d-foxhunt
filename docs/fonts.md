# Fonts

The app renders text with **1-bit bitmap fonts** in `be.fri3d.foxhunt/assets/fonts/*.bin`,
loaded at runtime via `lv.binfont_create` (see `assets/ui.py`). They're crisp pixel
fonts: one design-pixel maps to one screen pixel, no anti-aliasing, no runtime scaling.

## Current fonts

| `ui.py` helper | file | size | use |
|---|---|---|---|
| `font_small()`, `font_label()` | `pixelify_r11.bin` | em 10px, cap 7, descent 2 | body + labels |
| `font_title()` | `pixelify_b22.bin` | 22px | headers (placeholder — a purpose-built header font is TODO) |

A pixel font is **quantised**: you get its native size and integer multiples, nothing
between. Pixelify's native grid is ~11 design-px/em, so the old `r14`/`r16` bakes sat
*off* the grid and rendered unevenly — they were replaced by the single on-grid
`r11`. Body and label share it (one crisp tier); for a bigger title, design a new
font rather than scaling.

## The toolchain: `tools/bitmap_fonts/`

A self-contained, dependency-free workshop. Serve it over HTTP (the editor uses the
File System Access API + sibling files, so `file://` won't work):

```
cd tools/bitmap_fonts && python3 -m http.server   # then open editor.html (Chrome/Edge)
```

- **`editor.html`** — Aseprite-style editor: open a folder of `.bdf`/`.bin`, preview
  all fonts, edit any glyph. The canvas is **metrics-aware**: the editable grid is
  exactly `[0, advance)` wide × ascent..descent tall, with baseline / origin /
  advance / cap guides; editable advance-per-glyph and font ascent/descent. Tools:
  pencil (MacPaint toggle — click an on-pixel to erase the stroke, off-pixel to fill;
  size 1–4, square/round), eraser, line, rectangle, select (move/delete); undo/redo,
  zoom, minimap, word preview; `←`/`→` step glyphs. Save `.bdf`, Export/Import `.bin`.
- **`import-from-vector.html`** — how a `.bdf` is *born*: drop a vector pixel font
  (e.g. Pixelify Sans TTF), it auto-detects the native pixel grid, snaps to a clean
  1-bit bitmap, exports `.bdf`.
- **`font_codec.js`** — the engine (also Node-importable for tests): BDF ⇄ glyph model
  ⇄ LVGL `.bin`.
- **`fonts/`** — source-of-truth `.bdf` files (+ `CREDITS.md`, OFL).

### Workflow
1. Create a `.bdf` from a vector font with `import-from-vector.html`, **or** start
   fresh / edit an existing one in `editor.html`.
2. Edit glyphs and metrics in `editor.html`; **Save `.bdf`** (commit this — it's the
   diff-friendly source of truth, lives in `tools/bitmap_fonts/fonts/`).
3. **Export `.bin`** into `be.fri3d.foxhunt/assets/fonts/` (the deployed artifact).
4. Point a `ui.py` `font_*()` helper at the new `.bin`.

Keep the source `.bdf` and the deployed `.bin` in sync — re-export after editing.

## Why we write `.bin` directly (no `lv_font_conv`, no TTF)

The LVGL `.bin` is a **bitmap container** (tables `head`/`cmap`/`loca`/`glyf`, where
each glyph is `advanceWidth · bbox · raw pixel bits` — no curves). `lv_font_conv` only
ingests OpenType because its input stage rasterizes outlines→pixels via FreeType; it
**can't read BDF**. So the "obvious" path BDF→TTF→`lv_font_conv`→`.bin` re-vectorizes
then re-rasterizes our already-perfect pixels — and it's *lossy* (FreeType flattened
the sub-pixel bearings of `) = { } ~` in testing).

`font_codec.js` ports `lv_font_conv`'s serializer and writes `.bin` straight from the
bitmaps. It's verified **byte-identical** to `lv_font_conv --bpp 1 --no-compress` (with
the roundtrip distortion removed). Format spec:
<https://github.com/lvgl/lv_font_conv/blob/master/doc/font_spec.md>.

## Running on the emulator

The app is symlinked into a local MicroPythonOS checkout's `apps/`; the symlink name
must match the app id (`be.fri3d.foxhunt`):

```
ln -sfn /Users/fdb/Projects/fri3d-fox-hunt/be.fri3d.foxhunt \
  /Users/fdb/Source/MicroPythonOS/internal_filesystem/apps/be.fri3d.foxhunt
cd /Users/fdb/Source/MicroPythonOS && ./scripts/run_desktop.sh be.fri3d.foxhunt
```

`ui.py` falls back to the built-in font if a `.bin` fails to load (printing
`ui: binfont <name> failed`), so a missing/broken font degrades instead of crashing.
For a badge build, resolve the artwork symlink (`cp -rL`); the `.bin` files are plain
files and need no special handling.
