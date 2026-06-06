#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Run the Beestenjacht app on the macOS SDL emulator.
#
# Unlike the badge (which needs files copied onto its LittleFS), the desktop
# emulator reads the working tree live through a symlink in MicroPythonOS's
# apps/ dir, so edits show up on the next run with no copy step. This script
# just makes sure that symlink exists, then hands off to run_desktop.sh.
#
# Usage: scripts/run_on_mac.sh [-- <extra run_desktop.sh args>]
#
# Env overrides:
#   MPOS_DIR    MicroPythonOS checkout (default: ~/Source/MicroPythonOS)

PROJECT_DIR="$(pwd)"
APP_ID="com.fri3d.beestenjacht"
APP_SRC="$PROJECT_DIR/$APP_ID"
MPOS_DIR="${MPOS_DIR:-$HOME/Source/MicroPythonOS}"
RUN_DESKTOP="$MPOS_DIR/scripts/run_desktop.sh"
LINK="$MPOS_DIR/internal_filesystem/apps/$APP_ID"

# ── Sanity checks ────────────────────────────────────────────────────
[[ -d "$APP_SRC" ]]     || { echo "error: app dir not found: $APP_SRC" >&2; exit 1; }
[[ -f "$RUN_DESKTOP" ]] || { echo "error: run_desktop.sh not found: $RUN_DESKTOP" >&2
                             echo "       set MPOS_DIR to your MicroPythonOS checkout." >&2; exit 1; }

# ── Ensure the app is linked into MicroPythonOS's apps/ ───────────────
if [[ ! -e "$LINK" && ! -L "$LINK" ]]; then
    echo "Linking $APP_ID into $MPOS_DIR/internal_filesystem/apps/"
    ln -s "$APP_SRC" "$LINK"
elif [[ "$(readlink "$LINK" 2>/dev/null)" != "$APP_SRC" ]]; then
    echo "warning: $LINK exists but does not point at $APP_SRC" >&2
    echo "         leaving it as-is; remove it if you want this script to relink." >&2
fi

# ── Launch the emulator ──────────────────────────────────────────────
echo "Running $APP_ID on the macOS emulator..."
exec "$RUN_DESKTOP" "$APP_ID" "$@"
