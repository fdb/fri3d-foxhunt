#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Run the Foxhunt app on the macOS SDL emulator.
#
# This uses PREBUILT MicroPythonOS release artifacts (no compiling from
# source). Install and upgrade are automatic and pinned to MPOS_VERSION, so a
# fresh mac needs nothing but this script, and an install left behind by an
# older pin is replaced rather than silently used.
#
# Unlike the badge (which needs files copied onto its LittleFS), the desktop
# emulator reads the working tree live through a symlink in MicroPythonOS's
# apps/ dir, so edits show up on the next run with no copy step. This script
# makes sure the right OS is present and the symlink exists, then hands off to
# the OS's own run_desktop.sh.
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
# (data/com.enigmeta.foxhunt/), so this script makes that path a symlink and
# points it at a per-persona slot (com.enigmeta.foxhunt.default / .lora) before
# every launch. Switching persona never touches the other one's save, and a
# persona whose slot is empty simply onboards itself — which is exactly what
# the jager's first run must do, since its MAC has no account yet.
#
# Environment:
#   MPOS_DIR        MicroPythonOS install dir (default: ~/MicroPythonOS)
#   MPOS_VERSION    MicroPythonOS release to install (default: the pin below)
#
# FOXHUNT_BADGE_ID and FOXHUNT_FAKE_LORA are internal implementation details
# of --lora. They are cleared below so an inherited value cannot accidentally
# turn a normal emulator launch into a jager.

PROJECT_DIR="$(pwd)"
APP_ID="com.enigmeta.foxhunt"
# The desktop's second fake MAC. Must differ from registrar.badge_id's own
# fallback, and scripts/delete_account.sh --emulator-lora must know it too.
LORA_BADGE="A4:CF:12:9B:03:7F"
APP_SRC="$PROJECT_DIR/$APP_ID"
MPOS_DIR="${MPOS_DIR:-$HOME/MicroPythonOS}"
# The OS release this app is developed against. It must be >= 0.15.1: the app
# ships the flat layout (MANIFEST.JSON at the app root) and an older OS looks
# only in META-INF/, finds no launcher activity, and boots to the launcher with
# the app never started.
MPOS_VERSION="${MPOS_VERSION:-0.17.3}"
MPOS_REPO="https://github.com/MicroPythonOS/MicroPythonOS"
RUN_DESKTOP="$MPOS_DIR/scripts/run_desktop.sh"
BINARY="$MPOS_DIR/lvgl_micropython/build/lvgl_micropy_macOS"
LINK="$MPOS_DIR/internal_filesystem/apps/$APP_ID"

# ── Arguments ─────────────────────────────────────────────────────────
LORA=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lora)  LORA=1; shift ;;
        -h|--help) sed -n '5,42p' "$0"; exit 0 ;;
        --) shift; break ;;
        *) break ;;
    esac
done

# ── Sanity check: the app must exist locally ──────────────────────────
[[ -d "$APP_SRC" ]] || { echo "error: app dir not found: $APP_SRC" >&2; exit 1; }

# ── Ensure MicroPythonOS $MPOS_VERSION is on disk ─────────────────────
# Upstream publishes the two halves of a desktop install separately: the
# emulator binary as a per-arch release asset, and internal_filesystem/ +
# scripts/ inside the source tarball. This assembles them, so a fresh mac
# needs nothing but this script and no privately hosted bundle.
#
# The on-disk internal_filesystem/lib wins over anything frozen into the
# binary (run_desktop.sh puts "lib" before ".frozen" on sys.path), so the two
# halves must come from the SAME release or the OS runs as a version salad.
installed_version() {
    local info="$MPOS_DIR/internal_filesystem/lib/mpos/build_info.py"
    [[ -f "$info" ]] || return 0
    sed -n 's/.*release = "\(.*\)".*/\1/p' "$info" | head -1
}

install_mpos() {
    local staging tarball asset arch
    case "$(uname -m)" in
        arm64) arch="arm64" ;;
        x86_64) arch="intel" ;;
        *) echo "error: unsupported mac architecture $(uname -m)" >&2; exit 1 ;;
    esac
    asset="$MPOS_REPO/releases/download/$MPOS_VERSION/MicroPythonOS_${arch}_macOS_$MPOS_VERSION.bin"
    staging="$(mktemp -d -t MicroPythonOS)"
    tarball="$staging/src.tar.gz"

    echo "  GET $MPOS_REPO/archive/refs/tags/$MPOS_VERSION.tar.gz"
    curl -fL --progress-bar -o "$tarball" \
        "$MPOS_REPO/archive/refs/tags/$MPOS_VERSION.tar.gz"
    mkdir -p "$staging/new"
    tar -xzf "$tarball" -C "$staging/new" --strip-components=1 \
        "MicroPythonOS-$MPOS_VERSION/internal_filesystem" \
        "MicroPythonOS-$MPOS_VERSION/scripts"

    echo "  GET $asset"
    mkdir -p "$staging/new/lvgl_micropython/build"
    curl -fL --progress-bar -o "$staging/new/lvgl_micropython/build/lvgl_micropy_macOS" "$asset"
    chmod +x "$staging/new/lvgl_micropython/build/lvgl_micropy_macOS"

    # Carry the existing install's state across: every persona's save, and the
    # app symlinks other projects put in apps/ (each project's own run script
    # would relink its own, but not the others').
    if [[ -d "$MPOS_DIR/internal_filesystem" ]]; then
        for parent in data prefs; do
            [[ -d "$MPOS_DIR/internal_filesystem/$parent" ]] || continue
            mkdir -p "$staging/new/internal_filesystem/$parent"
            cp -R "$MPOS_DIR/internal_filesystem/$parent/." \
                  "$staging/new/internal_filesystem/$parent/"
        done
        for link in "$MPOS_DIR"/internal_filesystem/apps/*; do
            [[ -L "$link" ]] || continue
            cp -R "$link" "$staging/new/internal_filesystem/apps/"
        done
        local backup="$MPOS_DIR.$(installed_version || true)"
        [[ "$backup" == "$MPOS_DIR." ]] && backup="$MPOS_DIR.previous"
        rm -rf "$backup"
        mv "$MPOS_DIR" "$backup"
        echo "  Previous install kept at $backup (delete it when happy)"
    fi
    mkdir -p "$(dirname "$MPOS_DIR")"
    mv "$staging/new" "$MPOS_DIR"
    rm -rf "$staging"

    [[ -f "$BINARY" && -f "$RUN_DESKTOP" ]] || {
        echo "error: install is missing expected files:" >&2
        echo "       $BINARY" >&2
        echo "       $RUN_DESKTOP" >&2
        exit 1
    }
    echo "  Installed MicroPythonOS $MPOS_VERSION at $MPOS_DIR"
}

have="$(installed_version)"
if [[ ! -f "$BINARY" || ! -f "$RUN_DESKTOP" ]]; then
    echo "MicroPythonOS not found at $MPOS_DIR — installing $MPOS_VERSION..."
    install_mpos
elif [[ "$have" != "$MPOS_VERSION" ]]; then
    echo "MicroPythonOS at $MPOS_DIR is ${have:-unknown} — upgrading to $MPOS_VERSION..."
    install_mpos
fi

# ── Check the binary's Homebrew dependencies ──────────────────────────
# The release binary links Homebrew dylibs by absolute path (sdl2-compat, not
# the older sdl2). A missing one aborts in dyld before any Python runs, with a
# wall of "tried:" paths and no hint of the fix — so name the fix here.
while read -r lib; do
    [[ -f "$lib" ]] && continue
    echo "error: the emulator binary needs $lib" >&2
    echo "       install it with: brew install $(basename "$(dirname "$(dirname "$lib")")")" >&2
    exit 1
done < <(otool -L "$BINARY" | awk '/^\t\/opt\/homebrew/ {print $1}')

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
