#!/usr/bin/env bash
# Bake the source .bdf fonts into the LVGL .bin files the app loads.
#
# tools/bitmap_fonts/fonts/*.bdf  →  be.fri3d.foxhunt/assets/fonts/*.bin
#
# The .bdf is the source of truth (text, diffable, editable in editor.html);
# the .bin is the deployed artifact — LVGL's `lv.binfont_create` reads nothing
# else. Both are committed, because the badge has no build step: whatever sits
# in assets/ is what runs.
#
# The bake is the same code path as the editor's "Export .bin" button —
# tools/bitmap_fonts/font_codec.js, which is browser- and Node-importable — so
# this script and the editor produce byte-identical output. Node is the only
# requirement; nothing is installed.
#
# Usage:
#   scripts/bake_fonts.sh            # (re-)bake every font
#   scripts/bake_fonts.sh --check    # report stale/missing .bin, change nothing
#                                    # (exit 1 if anything is out of date — CI)
set -euo pipefail

cd "$(dirname "$0")/.."

mode="write"
case "${1:-}" in
    "")        mode="write" ;;
    --check)   mode="check" ;;
    *)         echo "usage: $0 [--check]" >&2; exit 2 ;;
esac

command -v node >/dev/null || {
    echo "bake_fonts: node is required (font_codec.js is JavaScript)" >&2
    exit 1
}

src_dir="tools/bitmap_fonts/fonts"
out_dir="be.fri3d.foxhunt/assets/fonts"

# The bake itself: read one .bdf, write one .bin. Kept inline so the toolchain
# stays two files (this script + font_codec.js) with no package.json.
bake() {
    node -e '
      const fs = require("fs");
      const C = require("./tools/bitmap_fonts/font_codec.js");
      const [bdf, out] = process.argv.slice(1);
      const font = C.parseBDF(fs.readFileSync(bdf, "utf8"));
      fs.writeFileSync(out, Buffer.from(C.lvBinFromGlyphs(font, { bpp: 1 })));
      console.error(`  ${font.glyphs.length} glyphs, ${fs.statSync(out).size} bytes`);
    ' "$1" "$2"
}

fail=0
for bdf in "$src_dir"/*.bdf; do
    name="$(basename "$bdf" .bdf)"
    out="$out_dir/$name.bin"

    if [[ "$mode" == "check" ]]; then
        tmp="$(mktemp)"
        trap 'rm -f "$tmp"' EXIT
        bake "$bdf" "$tmp" 2>/dev/null
        if [[ ! -f "$out" ]]; then
            echo "missing: $out"
            fail=1
        elif ! cmp -s "$tmp" "$out"; then
            echo "stale: $out (does not match $bdf)"
            fail=1
        fi
        rm -f "$tmp"
    else
        echo "baking: $bdf -> $out"
        bake "$bdf" "$out"
    fi
done

# A .bin with no .bdf beside it can't be regenerated. Flag it so it doesn't
# quietly become unmaintainable.
for bin in "$out_dir"/*.bin; do
    name="$(basename "$bin" .bin)"
    [[ -f "$src_dir/$name.bdf" ]] || echo "note: $bin has no .bdf source — cannot be re-baked"
done

if [[ "$mode" == "check" && "$fail" -ne 0 ]]; then
    echo "fonts out of date — run scripts/bake_fonts.sh" >&2
    exit 1
fi
