# Licensing

Three licences, split by what a file *is* rather than by where it sits — the
build generates artwork into code directories and code into the server tree, so
the directory is not a reliable guide.

| What | Licence | Text |
| --- | --- | --- |
| Code | **GPL-2.0-only** | [`LICENSE`](LICENSE) |
| Artwork | **CC BY-NC-SA 4.0** | [`LICENSES/CC-BY-NC-SA-4.0.txt`](LICENSES/CC-BY-NC-SA-4.0.txt) |
| Fonts (third-party) | **OFL-1.1** | [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt) |

Copyright © 2026 Frederik De Bleser and Hans Robbeers. Who made what is under
[Credits](#credits).

## Code — GPL-2.0-only

Everything that is not artwork or a font: the badge app (`com.enigmeta.foxhunt/`),
the Cloudflare worker (`server/src/`), the scripts, the tools, the tests, the
docs.

GPL-2.0 **only**, not "or later" — the same choice git makes, and the reason its
licence text is the copy in `LICENSE`.

Nothing this depends on gets in the way of that: MicroPythonOS, MicroPython and
LVGL are all MIT.

## Artwork — CC BY-NC-SA 4.0

The drawn assets and everything mechanically derived from them. Sources first:

- `artwork/**` — the Aseprite files and PNGs: `animals/` (the creatures),
  `companions/` (maatje heads, accessories), `title-screen/`.

Then the generated derivatives, which carry the same licence as what they were
baked from even though they look like code:

- `com.enigmeta.foxhunt/assets/sprites.bin` and `assets/atlas.py` — the packed
  atlas and its palette index (`scripts/bake_sprites.sh`).
- `com.enigmeta.foxhunt/assets/title-screen/title-screen.png` — palettized mirror
  of the banner.
- `server/static/art/silhouettes/*.png`, `server/static/vos.png` — the public
  site's silhouettes and favicon.
- `server/src/lib/companion-art.ts` — companion layers inlined as data URIs
  (`scripts/bake_server_art.sh`).
- `server/src/lib/icon-art.ts` — SVG run geometry baked from the `ICONS` grids
  (`scripts/bake_server_icons.sh`).
- `server/static/screens/*.png` — screenshots, since what they show is the art.

One boundary worth stating outright, because no directory rule catches it: the
`ICONS` tables in `com.enigmeta.foxhunt/assets/art.py` are **pixel art written as
Python**. The grids are artwork; the module around them is code. That is also
why `icon-art.ts` above is listed as artwork — it is those same grids, baked.

Non-commercial: reuse the pixels in your own badge app, a fork, a zine, a
workshop. Selling them, or a product built around them, needs a word first.

The BY half of the licence wants a credit, so here is one that fits in a
caption: *"Vossenjacht — pixel art by Erlin, Fran and Fien, CC BY-NC-SA 4.0"*.

## Fonts — SIL Open Font License 1.1

Not ours to relicense, and excluded from both of the above:

- `tools/bitmap_fonts/fonts/pixelify_*.bdf` — 1-bit bitmaps derived from
  **Pixelify Sans** by Stefie Justprince.
- `com.enigmeta.foxhunt/assets/fonts/*.bin` — the LVGL bakes of those
  (`scripts/bake_fonts.sh`).

The OFL permits the derivation and the redistribution, and the result stays under
the OFL. Provenance and credit live in
[`tools/bitmap_fonts/fonts/CREDITS.md`](tools/bitmap_fonts/fonts/CREDITS.md);
keep both that file and `LICENSES/OFL-1.1.txt` with any build that ships the
fonts — which is every badge build, since the app draws all its text with them.

## Credits

- **Frederik De Bleser** — the game: badge app, server.
- **Hans Robbeers** — the LoRa side: the radio work that turns a transmitter
  hidden in a field into a fox this app can hunt.
- **Erlin, Fran and Fien** — pixel art.
- **Stefie Justprince** — Pixelify Sans, the font every screen is drawn with
  (OFL-1.1, see above).

## Shipping

The `.mpk` that goes to an app store carries the fonts and the baked artwork, so
it is a distribution of all three licences at once. Nothing about that is unusual
— it just means the credit and the licence texts travel with the repo, which is
what this file and `CREDITS.md` are for.

Per-file SPDX headers are deliberately not used. The app is ~5k lines across 20
modules with a flash budget measured in 4 KB blocks, and this table says the same
thing in one place.
