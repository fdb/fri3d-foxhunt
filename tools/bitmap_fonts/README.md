# bitmap_fonts — LVGL pixel-font workshop

A self-contained, browser-based editor for the bitmap fonts the Foxhunt app
uses. Think "a tiny Aseprite for font glyphs." We **edit `.bdf`** (plain text,
diff-friendly, version-controlled) and **export `.bin`** (the LVGL binary font
loaded at runtime via `lv.binfont_create`). We can also **import `.bin`** back
into editable glyphs.

## Files
- `editor.html` — the editor: a three-screen, Aseprite-style tool (library →
  glyph grid → glyph editor). Open via a local server; needs the File System
  Access API, so **Chrome/Edge**.
- `styles.css` — the editor's visual system (oklch grayscale + accent, light/dark
  themes, IBM Plex). Adopted from a **Claude Design** handoff ("PixelForge"); the
  design had no font metrics, so the metrics model (advance width, ascent/descent,
  baseline-relative bboxes, real file I/O) is ours. See *Design provenance* below.
- `font_codec.js` — dependency-free, isomorphic codec: BDF ⇄ glyph model ⇄ LVGL
  `.bin`. Used by the editor and by Node tests.
- `import-from-vector.html` — the upstream importer: drop a vector pixel font
  (e.g. Pixelify Sans TTF), auto-calibrate its native pixel grid, snap to a
  crisp 1-bit bitmap, export BDF. This is how a `.bdf` gets *created* from a
  vector source in the first place.
- `fonts/` — the source-of-truth `.bdf` library (and `CREDITS.md`).

### Running it
The editor loads `styles.css` + `font_codec.js` as siblings and uses the File
System Access API, so serve the folder over HTTP rather than `file://`:
`cd tools/bitmap_fonts && python3 -m http.server` → open `editor.html`. IBM Plex
is pulled from Google Fonts (falls back to system fonts offline).

The editor canvas is **metrics-aware**: its grid spans the glyph's bearing→advance
columns and ascent→descent rows, with red baseline / green origin / gold advance /
blue cap guides, an editable advance width per glyph, and font-level ascent/descent.
Tools: pencil (size 1–4, square/round), eraser, line, rectangle (outline/fill),
rect-select (move + delete); undo/redo, zoom, minimap, word preview, keyboard
shortcuts (B/E/L/U/M, ⌘Z/⌘⇧Z, 1–4, +/−, Esc, Del).

### Design provenance
The look comes from a Claude Design bundle (`pixel-font-editor`, "PixelForge").
Per its README we recreated the visuals pixel-perfectly in the tech that fits this
repo (vanilla JS, no React/Babel/CDN build) rather than copying the prototype's
structure. The prototype modelled glyphs as fixed N×N bitmaps with localStorage
persistence and **no metrics** — replacing that with real metrics + BDF/.bin file
I/O was the point of the integration.

## Why we write `.bin` directly (no TTF roundtrip)

The LVGL `.bin` is a **bitmap container**, not vector: tables `head` / `cmap` /
`loca` / `glyf`, where each `glyf` entry is just
`advanceWidth · bbox.x · bbox.y · bbox.width · bbox.height · raw pixel bits`
(bit-packed, MSB-first, big-endian). No curves anywhere.

`lv_font_conv` only ingests OpenType (TTF/OTF/WOFF) because its single input
adapter rasterizes outlines→pixels via FreeType; everything after that is
bitmap serialization. So the "obvious" path BDF→TTF→`lv_font_conv`→`.bin`
**re-vectorizes then re-rasterizes** our already-perfect pixels — and we proved
it is *lossy*: FreeType flattened the sub-pixel left bearings of 5 glyphs
(`) = { } ~`) during the roundtrip.

`font_codec.js` ports `lv_font_conv`'s serializer faithfully and writes the
`.bin` straight from the BDF bitmaps. Verified **byte-identical** to
`lv_font_conv --bpp 1 --no-compress` when fed the same glyph metrics — with the
roundtrip distortion removed. One hop, no FreeType, no Node.

## LVGL binary font format — spec

Authoritative reference (table layouts, cmap subtable formats, bit-field
packing, compression):

  https://github.com/lvgl/lv_font_conv/blob/master/doc/font_spec.md

Notes from porting it (see `font_codec.js`):
- `bpp 1` ⇒ compression id `0` (raw); no prefilter/RLE.
- No kerning ⇒ `kern` table omitted; `head.tables_count = 3` (cmap, loca, glyf).
- cmap picks the smallest of `format0` / `format0_tiny` / `sparse_tiny` per run
  of codepoints (breadth-first planner). Contiguous ASCII → one `format0_tiny`.
- Quirk replicated for byte-exactness: `head` writes `underline_thickness` over
  `underline_position` (upstream bug).

## Toolchain check
`lv_font_conv` 1.5.3 is reachable via `npx lv_font_conv` (no install). It does
**not** read BDF — that's why the direct codec exists.
