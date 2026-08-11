#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Build the app-store package (.mpk) with BYTECODE instead of source.
#
# An .mpk is a stored zip of the app dir that the OS streams straight into
# apps/<fullname> (AppManager.download_and_install_package). The store's own
# bundler (MicroPythonOS scripts/bundle_apps.sh) zips the source tree as-is:
# for this app that is ~516 KB of .py, most of it comments — which the badge
# then keeps on LittleFS and re-compiles on every cold start. This script
# stages the same badge-clean copy the USB deploy ships (mpy-cross -O2,
# -march=xtensawin) and zips THAT: ~272 KB installed, no compile at start.
# The manifest's "assets/foxhunt.py" entrypoint still works — the OS imports
# by module name, so foxhunt.mpy loads the same (proven by the USB deploy).
#
# Two couplings to know about:
#   - The .mpy format must match the firmware's bytecode version, so this
#     uses the in-tree mpy-cross from the same checkout that built the
#     firmware. A badge on a different MicroPythonOS build may refuse it;
#     source .mpk's don't have that problem.
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
MPY_CROSS="${MPY_CROSS:-/Users/fdb/Source/MicroPythonOS/lvgl_micropython/lib/micropython/mpy-cross/build/mpy-cross}"
[[ -x "$MPY_CROSS" ]] || { echo "error: mpy-cross not found at $MPY_CROSS (build the firmware checkout first, or set MPY_CROSS)" >&2; exit 1; }

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
echo "  $files files, $(stat -f%z "$mpk") bytes ($version, $(git rev-parse --short HEAD 2>/dev/null || echo unversioned))"
