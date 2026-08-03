#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Deploy the Foxhunt app onto a USB-connected Fri3d badge running
# MicroPythonOS. Apps are plain files on the device's LittleFS, so this does
# NOT touch firmware — it stages a badge-clean copy (desktop cruft dropped)
# and pushes it over the serial REPL.
#
# Usage: scripts/deploy_to_badge.sh [--start] [--port /dev/cu.usbmodemXXX]
#
#   --start          launch the app on the badge after installing
#   --port PORT      serial port (default: auto-detect /dev/cu.usbmodem*)
#
# Env overrides:
#   MPOS_DIR         MicroPythonOS checkout (default: ~/Source/MicroPythonOS)
#   BADGE_PORT       same as --port

PROJECT_DIR="$(pwd)"
APP_ID="be.fri3d.foxhunt"
APP_SRC="$PROJECT_DIR/$APP_ID"
MPOS_DIR="${MPOS_DIR:-$HOME/Source/MicroPythonOS}"
CONTROLLER="$MPOS_DIR/scripts/mpos_controller.py"

START=0
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start) START=1; shift ;;
        --port)  PORT="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '4,20p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

# ── Sanity checks ────────────────────────────────────────────────────
[[ -d "$APP_SRC" ]]    || { echo "error: app dir not found: $APP_SRC" >&2; exit 1; }
[[ -f "$CONTROLLER" ]] || { echo "error: controller not found: $CONTROLLER" >&2
                            echo "       set MPOS_DIR to your MicroPythonOS checkout." >&2; exit 1; }
command -v uv >/dev/null || { echo "error: 'uv' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

# ── Auto-detect serial port ──────────────────────────────────────────
if [[ -z "$PORT" ]]; then
    ports=(/dev/cu.usbmodem*)
    if [[ ! -e "${ports[0]}" ]]; then
        echo "error: no /dev/cu.usbmodem* device found. Is the badge plugged in?" >&2
        echo "       Pass --port or set BADGE_PORT to override." >&2
        exit 1
    fi
    if [[ ${#ports[@]} -gt 1 ]]; then
        echo "error: multiple serial devices found; pass --port to pick one:" >&2
        printf '       %s\n' "${ports[@]}" >&2
        exit 1
    fi
    PORT="${ports[0]}"
fi
[[ -e "$PORT" ]] || { echo "error: serial port not found: $PORT" >&2; exit 1; }

# Older controllers took --serial-port for their own REPL but spawned mpremote
# with no `connect`, so file copies went to mpremote's auto-detected device —
# sorted(comports())[0]. With one badge that is always the right one and the bug
# is invisible; with two it silently flashes the wrong badge. Only refuse when
# it could actually bite: more than one device attached AND a stale controller.
if ! grep -q '_mpremote_cmd' "$CONTROLLER"; then
    attached=(/dev/cu.usbmodem*)
    if [[ -e "${attached[0]}" && ${#attached[@]} -gt 1 ]]; then
        echo "error: $CONTROLLER predates the mpremote --port fix, and more than" >&2
        echo "       one serial device is attached. It would ignore --port for the" >&2
        echo "       file copy and flash whichever device sorts first. Update your" >&2
        echo "       MicroPythonOS checkout, or unplug the other device." >&2
        exit 1
    fi
fi

# ── Stage a badge-clean copy ─────────────────────────────────────────
STAGE_ROOT="$(mktemp -d)"
trap 'rm -rf "$STAGE_ROOT"' EXIT
STAGE="$STAGE_ROOT/$APP_ID"

cp -R "$APP_SRC" "$STAGE"
# Desktop-only cruft: CPython bytecode caches and Finder metadata.
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '.DS_Store' -delete

echo "Deploying $APP_ID -> $PORT"

# uv run puts its venv's python3 first on PATH, so the mpremote subprocess the
# controller spawns inherits these deps too.
RUN=(uv run --with pyserial --with platformdirs "$CONTROLLER" --serial-port "$PORT")

# ── Install ──────────────────────────────────────────────────────────
"${RUN[@]}" installapp "$STAGE"

# ── Optionally launch ────────────────────────────────────────────────
if [[ "$START" -eq 1 ]]; then
    echo "Starting $APP_ID on badge..."
    "${RUN[@]}" startapp "$APP_ID"
fi

echo "Done."
