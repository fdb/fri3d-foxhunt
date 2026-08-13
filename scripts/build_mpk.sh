#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Build the app-store package (.mpk) with BYTECODE instead of source.
#
# An .mpk is a stored zip of the app dir that the OS streams straight into
# apps/<fullname> (AppManager.download_and_install_package). The store's own
# bundler (MicroPythonOS scripts/bundle_apps.sh) zips the source tree as-is:
# for this app that is 473 KB of .py, most of it comments — which the badge
# then keeps on LittleFS and re-compiles on every cold start. This script
# stages the same badge-clean copy the USB deploy ships (mpy-cross,
# -march=xtensawin) and zips THAT: 145 KB installed, no compile at start.
# The manifest's "assets/foxhunt.py" entrypoint still works — the OS imports
# by module name, so foxhunt.mpy loads the same (proven by the USB deploy).
#
# BYTECODE IS THE ONLY FLAVOUR WE SHIP, and that is settled rather than
# pending. A source .mpk is the portable one — it survives a firmware whose
# bytecode version moved — so it keeps looking like the safer thing to also
# publish. It was tried and it does not fit: 473 KB against 145 KB installed,
# 528 KB against 197 KB once LittleFS bills its 4 KB per file, on a 7 MiB
# partition a factory badge arrives with nearly full (Size budget in
# CLAUDE.md). The compile at every cold start wants the heap as well, on a
# device that already spends a second on a mark-sweep. Do not add a --source
# mode to "cover" other badges; cover them by matching their bytecode.
#
# Two couplings to know about:
#   - The .mpy format must match the firmware's bytecode version. This uses
#     the in-tree mpy-cross from the checkout that built the firmware when
#     there is one, else scripts/get_mpy_cross.sh rebuilds exactly that
#     compiler from MicroPythonOS's own submodule pins — same bytes, no
#     checkout needed, which is what lets CI produce the package.
#   - art_fast.mpy carries xtensawin native code. On any non-ESP32-S3 device
#     its import fails, which art.py already catches (desktop fallback).
#
# STRIPPED harder than the USB deploy: -O3, not -O2. The only difference is
# the line-number table — the deploy keeps it because a badge on your desk
# should give line-numbered tracebacks, but a store install lands on badges
# whose free space we cannot control, and there size wins (~6% smaller).
# A field traceback from a store install still names module + function,
# just not the line.
#
# The zip recipe matches bundle_apps.sh byte-for-byte where it matters:
# stored (-0) because that is the proven streaming-unzip path, no extra
# attributes (-X), fixed mtimes and sorted entries so the same tree always
# produces the same .mpk.
#
# Usage: scripts/build_mpk.sh
# Output: dist/com.enigmeta.foxhunt_<version>.mpk

APP_ID="com.enigmeta.foxhunt"
APP_SRC="$PWD/$APP_ID"
DIST="$PWD/dist"

command -v uv >/dev/null || { echo "error: 'uv' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

# mpy-cross, in order of preference: an explicit override, the developer's own
# firmware checkout (already there, nothing to build), else fetch-and-build one
# from the pins MicroPythonOS publishes. That last leg is what lets a build
# server produce the package at all — see scripts/get_mpy_cross.sh.
IN_TREE_MPY_CROSS="$HOME/Source/MicroPythonOS/lvgl_micropython/lib/micropython/mpy-cross/build/mpy-cross"
if [[ -z "${MPY_CROSS:-}" && -x "$IN_TREE_MPY_CROSS" ]]; then
    MPY_CROSS="$IN_TREE_MPY_CROSS"
fi
MPY_CROSS="${MPY_CROSS:-$(scripts/get_mpy_cross.sh)}"
[[ -x "$MPY_CROSS" ]] || { echo "error: mpy-cross not found at $MPY_CROSS (set MPY_CROSS, or let scripts/get_mpy_cross.sh build one)" >&2; exit 1; }

version=$(uv run python -c "import json; print(json.load(open('$APP_SRC/META-INF/MANIFEST.JSON'))['version'])")

# ── Stage a badge-clean copy, compiled to .mpy (same as deploy_to_badge) ──
STAGE_ROOT="$(mktemp -d)"
trap 'rm -rf "$STAGE_ROOT"' EXIT
STAGE="$STAGE_ROOT/$APP_ID"
cp -R "$APP_SRC" "$STAGE"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '.DS_Store' -delete
while IFS= read -r f; do
    "$MPY_CROSS" -s "${f#"$STAGE/"}" -O3 -march=xtensawin -o "${f%.py}.mpy" "$f"
    rm "$f"
done < <(find "$STAGE" -name '*.py' -type f)

# ── Zip it the way the store does: stored, deterministic ─────────────
mkdir -p "$DIST"
mpk="$DIST/${APP_ID}_${version}.mpk"
rm -f "$mpk"
find "$STAGE_ROOT" -exec touch -t 202501010000.00 {} \;
(cd "$STAGE_ROOT" && { find "$APP_ID" -type d; find "$APP_ID" -type f; } | sort | TZ=CET zip -q -X -r0 "$mpk" -@)

files=$(find "$STAGE" -type f | wc -l | tr -d ' ')
echo "built $mpk"
# `wc -c <file` rather than stat: BSD wants -f%z and GNU wants -c%s, and this
# script now runs on both.
echo "  $files files, $(wc -c <"$mpk" | tr -d ' ') bytes ($version, $(git rev-parse --short HEAD 2>/dev/null || echo unversioned))"
