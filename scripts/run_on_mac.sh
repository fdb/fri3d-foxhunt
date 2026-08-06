#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Run the Foxhunt app on the macOS SDL emulator.
#
# This uses a PREBUILT MicroPythonOS package (no compiling from source). If the
# package isn't on disk yet it's downloaded and unzipped automatically, so a
# fresh mac needs nothing but this script.
#
# Unlike the badge (which needs files copied onto its LittleFS), the desktop
# emulator reads the working tree live through a symlink in MicroPythonOS's
# apps/ dir, so edits show up on the next run with no copy step. This script
# makes sure the package is present and the symlink exists, then hands off to
# the package's own run_desktop.sh.
#
# Usage: scripts/run_on_mac.sh [--lora] [-- <extra run_desktop.sh args>]
#
# Options:
#   --lora    Run as a badge WITH a LoRa antenna. Two things, and both are
#             needed for the jager half of the game to be reachable at all:
#             * The antenna. Desktop has no radio, so registrar.has_lora() is
#               false and instellingen -> WORD JAGER answers "geen antenne
#               gevonden" — there is no way to mint a hunter_id.
#             * A second MAC. badge_id is the account key, so sharing the one
#               desktop MAC would put the jager and the verzamelaar on a single
#               server account: the second registration meets the first as
#               "BADGE AL BEKEND" and adopts it instead of starting over.
#             Both are env overrides read by registrar.py, which the badge's
#             MicroPython cannot even see (no os.getenv on ESP32).
#
# Each persona keeps its OWN save. The app reads one fixed path
# (data/be.fri3d.foxhunt/), so this script makes that path a symlink and
# points it at a per-persona slot (be.fri3d.foxhunt.default / .lora) before
# every launch. Switching persona never touches the other one's save, and a
# persona whose slot is empty simply onboards itself — which is exactly what
# the jager's first run must do, since its MAC has no account yet.
#
# Environment:
#   MPOS_DIR        prebuilt MicroPythonOS dir (default: ~/MicroPythonOS)
#   MPOS_PKG_URL    download URL for the prebuilt macOS package zip
#
# FOXHUNT_BADGE_ID and FOXHUNT_FAKE_LORA are internal implementation details
# of --lora. They are cleared below so an inherited value cannot accidentally
# turn a normal emulator launch into a jager.

PROJECT_DIR="$(pwd)"
APP_ID="be.fri3d.foxhunt"
# The desktop's second fake MAC. Must differ from registrar.badge_id's own
# fallback, and scripts/delete_account.sh --emulator-lora must know it too.
LORA_BADGE="A4:CF:12:9B:03:7F"
APP_SRC="$PROJECT_DIR/$APP_ID"
MPOS_DIR="${MPOS_DIR:-$HOME/MicroPythonOS}"
MPOS_PKG_URL="${MPOS_PKG_URL:-https://debleser.s3-eu-central-1.amazonaws.com/2026-fri3d-badge/MicroPythonOS-macOS-0.12.0.zip}"
RUN_DESKTOP="$MPOS_DIR/scripts/run_desktop.sh"
BINARY="$MPOS_DIR/lvgl_micropython/build/lvgl_micropy_macOS"
LINK="$MPOS_DIR/internal_filesystem/apps/$APP_ID"

# ── Arguments ─────────────────────────────────────────────────────────
LORA=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lora)  LORA=1; shift ;;
        -h|--help) sed -n '5,43p' "$0"; exit 0 ;;
        --) shift; break ;;
        *) break ;;
    esac
done

# ── Sanity check: the app must exist locally ──────────────────────────
[[ -d "$APP_SRC" ]] || { echo "error: app dir not found: $APP_SRC" >&2; exit 1; }

# ── Ensure the prebuilt MicroPythonOS package is on disk ──────────────
# The zip unpacks to a top-level "MicroPythonOS/" dir, so we extract it into
# the parent of $MPOS_DIR. We consider the package present once both the
# emulator binary and run_desktop.sh exist.
if [[ ! -f "$BINARY" || ! -f "$RUN_DESKTOP" ]]; then
    echo "Prebuilt MicroPythonOS not found at $MPOS_DIR — downloading..."
    parent="$(dirname "$MPOS_DIR")"
    tmp_zip="$(mktemp -t MicroPythonOS.XXXXXX).zip"
    trap 'rm -f "$tmp_zip"' EXIT

    echo "  GET $MPOS_PKG_URL"
    curl -fL --progress-bar -o "$tmp_zip" "$MPOS_PKG_URL"

    echo "  Unzipping into $parent/"
    mkdir -p "$parent"
    unzip -q -o "$tmp_zip" -d "$parent"

    [[ -f "$BINARY" && -f "$RUN_DESKTOP" ]] || {
        echo "error: package unpacked but expected files are missing:" >&2
        echo "       $BINARY" >&2
        echo "       $RUN_DESKTOP" >&2
        exit 1
    }
    chmod +x "$BINARY"
    echo "  Installed MicroPythonOS at $MPOS_DIR"
fi

# ── Ensure the app is linked into MicroPythonOS's apps/ ───────────────
if [[ ! -e "$LINK" && ! -L "$LINK" ]]; then
    echo "Linking $APP_ID into $MPOS_DIR/internal_filesystem/apps/"
    ln -s "$APP_SRC" "$LINK"
elif [[ "$(readlink "$LINK" 2>/dev/null)" != "$APP_SRC" ]]; then
    echo "warning: $LINK exists but does not point at $APP_SRC" >&2
    echo "         leaving it as-is; remove it if you want this script to relink." >&2
fi

# ── Persona ──────────────────────────────────────────────────────────
# registrar.py reads both of these through os.getenv, which exists on the
# desktop port only. Always say which account this run is, because the server
# side of a desktop run is real and permanent.
PERSONA="default"
unset FOXHUNT_FAKE_LORA FOXHUNT_BADGE_ID
if [[ "$LORA" -eq 1 ]]; then
    PERSONA="lora"
    export FOXHUNT_FAKE_LORA=1
    export FOXHUNT_BADGE_ID="$LORA_BADGE"
    echo "Persona: jager (faked LoRa antenna), badge $LORA_BADGE"
else
    echo "Persona: verzamelaar (no antenna), the default desktop badge"
fi

# ── Point the save path at this persona's slot ────────────────────────
# SharedPreferences resolves data/$APP_ID/config.json relative to
# internal_filesystem/ (older builds used prefs/, so both parents are
# handled). Making $APP_ID a symlink into a per-persona slot gives every
# persona its own save without the app knowing: switching never touches the
# other slot, and an empty slot replays onboarding by itself.
for parent in data prefs; do
    pdir="$MPOS_DIR/internal_filesystem/$parent"
    live="$pdir/$APP_ID"
    slot="$pdir/$APP_ID.$PERSONA"
    # Migration, once: a real directory predates the slot scheme and is the
    # default persona's save. Rename, never delete.
    if [[ -d "$live" && ! -L "$live" ]]; then
        echo "Moving existing save to its slot: $parent/$APP_ID.default"
        mv "$live" "$pdir/$APP_ID.default"
    fi
    # The slot must exist before the app runs: SharedPreferences mkdirs the
    # literal path, and a dangling symlink makes that mkdir fail as EEXIST.
    mkdir -p "$slot"
    ln -sfn "$slot" "$live"
done

# ── Launch the emulator ──────────────────────────────────────────────
echo "Running $APP_ID on the macOS emulator..."
exec "$RUN_DESKTOP" "$APP_ID" "$@"
