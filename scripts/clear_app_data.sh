#!/usr/bin/env bash
# Wipe Foxhunt's saved state so the next run starts as a fresh hunter.
#
# The app persists everything (profile, caught ids, companion stats) through
# mpos.SharedPreferences, which is one config.json in a per-app directory,
# resolved relative to the filesystem root of whichever target is running:
# the MicroPythonOS checkout's internal_filesystem/ on desktop, LittleFS on
# the badge. MPOS versions disagree on the parent dir — the checkout writes
# data/<app>/, the badge firmware writes prefs/<app>/ — so both are cleared.
# The app re-creates whichever it uses on the next commit().
#
# Usage:
#   scripts/clear_app_data.sh                    # local (emulator) data only
#   scripts/clear_app_data.sh --badge            # local + connected badge (asks first)
#   scripts/clear_app_data.sh --badge --port /dev/cu.usbmodemXXX
#
# Env overrides:
#   MPOS_DIR         MicroPythonOS checkout (default: ~/Source/MicroPythonOS)
#   BADGE_PORT       same as --port
set -euo pipefail

cd "$(dirname "$0")/.."

APP_ID="be.fri3d.foxhunt"
MPOS_DIR="${MPOS_DIR:-$HOME/Source/MicroPythonOS}"
CONTROLLER="$MPOS_DIR/scripts/mpos_controller.py"
LOCAL_ROOT="$MPOS_DIR/internal_filesystem"

BADGE=0
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --badge) BADGE=1; shift ;;
        --port)  PORT="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

# ── Local (desktop emulator) ─────────────────────────────────────────
cleared=0
for parent in data prefs; do
    dir="$LOCAL_ROOT/$parent/$APP_ID"
    if [[ -d "$dir" ]]; then
        echo "Clearing local app data: $dir"
        rm -rf "$dir"
        cleared=1
    fi
done
[[ "$cleared" -eq 1 ]] || echo "Local app data already clean (nothing under $LOCAL_ROOT)"

[[ "$BADGE" -eq 1 ]] || exit 0

# ── Badge ────────────────────────────────────────────────────────────
[[ -f "$CONTROLLER" ]] || { echo "error: controller not found: $CONTROLLER" >&2
                            echo "       set MPOS_DIR to your MicroPythonOS checkout." >&2; exit 1; }
command -v uv >/dev/null || { echo "error: 'uv' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

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

# Erasing a badge is not undoable and the badge on the desk may not be yours,
# so make it a deliberate act: an explicit "yes", typed at a real terminal.
if [[ ! -t 0 ]]; then
    echo "error: --badge needs an interactive terminal to confirm" >&2
    exit 1
fi
echo
echo "About to ERASE $APP_ID's saved state on the badge at $PORT."
echo "That is the hunter profile, caught creatures and companion stats"
echo "on that device. There is no undo."
read -r -p "Type 'yes' to continue: " reply
if [[ "$reply" != "yes" ]]; then
    echo "Aborted — badge untouched."
    exit 1
fi

# Connecting resets the badge (DTR/RTS), so the app isn't running and can't
# write its in-memory prefs back over us after the delete.
echo "Clearing badge app data on $PORT..."
out="$(uv run --with pyserial --with platformdirs "$CONTROLLER" \
        --serial-port "$PORT" exec <<PY
import os


def rm(path):
    """Recursive delete; -1 if path does not exist."""
    try:
        is_dir = os.stat(path)[0] & 0x4000
    except OSError:
        return -1
    if is_dir:
        for entry in os.listdir(path):
            rm(path + "/" + entry)
        os.rmdir(path)
    else:
        os.remove(path)
    return 0


hits = [p for p in ("data/$APP_ID", "prefs/$APP_ID") if rm(p) == 0]
print("RESULT:", ", ".join(hits) if hits else "NOTHING")
PY
)"

# The REPL folds exceptions into its output, so trust the sentinel, not $?.
case "$out" in
    *"RESULT: NOTHING"*) echo "Badge app data already clean." ;;
    *"RESULT: "*)        echo "Badge app data cleared (${out##*RESULT: })." ;;
    *)                   echo "error: badge wipe did not confirm; device said:" >&2
                         echo "$out" >&2
                         exit 1 ;;
esac
