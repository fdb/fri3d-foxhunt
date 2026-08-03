#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Deploy the Foxhunt app onto a USB-connected Fri3d badge running
# MicroPythonOS. Apps are plain files on the device's LittleFS, so this does
# NOT touch firmware — it stages a badge-clean copy (desktop cruft dropped)
# and pushes it over the serial REPL.
#
# Installing over a *running* app is not enough on its own, so this also:
#   1. returns the badge to the launcher, so no activity holds the old code;
#   2. removes the previous install first, so the badge mirrors the source
#      (mpremote only ever copies, so orphans pile up until LittleFS is full);
#   3. drops the app's modules from sys.modules, so the next launch re-imports
#      from disk instead of reusing the previous run's cached modules.
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
            sed -n '5,24p' "$0"; exit 0 ;;
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
# --no-reset skips the DTR/RTS toggle before each REPL call: the badge speaks
# USB-CDC natively, so those lines reach nothing and we only pay the 1.7s settle.
REPL=("${RUN[@]}" --no-reset)
APP_DIR="apps/$APP_ID"

# An interrupted mpremote can leave the badge in a raw-REPL state the controller
# cannot talk its way out of: it dies in wait_for_boot with "aioREPL prompt not
# found" and every later deploy dies the same way, so the badge looks bricked.
# Ctrl-B plus a drain is what recovered it by hand. The controller does clear a
# *clean* raw REPL by itself, so this only earns its keep on the messier state
# left mid-transfer — which is exactly the one you cannot recover from. Costs a
# second and is harmless at the normal prompt, where Ctrl-B reprints the banner.
wake_repl() {
    uv run --with pyserial python - "$PORT" <<'EOF'
import sys, time, serial
with serial.Serial(sys.argv[1], 115200, timeout=0.2) as s:
    s.write(b"\x02")
    time.sleep(0.8)
    s.read(8192)
EOF
}

# ── Return to the launcher ───────────────────────────────────────────
# Overwriting the files under a live activity leaves it running old code with
# new code on disk. Stop it first; onDestroy also lets the app drop its timers.
echo "Returning badge to launcher..."
wake_repl
"${REPL[@]}" exec >/dev/null <<'PY'
from mpos import AppManager
AppManager.restart_launcher()
PY

# ── Wipe the installed copy ──────────────────────────────────────────
# `mpremote fs cp -r` only ever writes, so a file that leaves the source stays
# on the badge forever — that is how 25 __pycache__/*.pyc, the retired
# mascot.py and a whole superseded assets/sprites/ tree filled LittleFS. The
# install re-uploads every file regardless, so mirroring the directory costs
# nothing over pruning a diff and cannot leave an orphan behind. Save data is
# safe: it lives in data/be.fri3d.foxhunt/, not in the app dir.
# Iteratively, not recursively — MicroPython's stack blows well before a
# recursive walk of this tree finishes.
echo "Removing previous install from badge..."
"${REPL[@]}" exec <<PY
import os
root = "$APP_DIR"
dirs = []
try:
    os.stat(root)
    dirs.append(root)
except OSError:
    print("nothing installed yet")
i = 0
while i < len(dirs):
    for n in os.listdir(dirs[i]):
        f = dirs[i] + "/" + n
        if os.stat(f)[0] & 0x4000:
            dirs.append(f)
        else:
            os.remove(f)
    i += 1
for d in sorted(dirs, key=len, reverse=True):
    os.rmdir(d)
s = os.statvfs("/")
print("removed {} dirs, {} bytes now free".format(len(dirs), s[0] * s[3]))
PY

# ── Install ──────────────────────────────────────────────────────────
# Two reasons this retries rather than running once. LittleFS reclaims the just
# -freed blocks lazily, and that erase burst blocks the MicroPython VM long
# enough for mpremote's raw-REPL handshake to time out ("timeout waiting for
# first EOF reception"). And because the wipe already happened, a failed copy
# leaves a half-installed app — so give it a settle and three real attempts.
sleep 3
installed=0
for attempt in 1 2 3; do
    if "${RUN[@]}" installapp "$STAGE"; then
        installed=1
        break
    fi
    echo "install attempt $attempt/3 failed; letting the badge settle..." >&2
    sleep 5
    wake_repl
done
if [[ "$installed" -ne 1 ]]; then
    echo "error: install failed three times. The badge now holds a partial copy" >&2
    echo "       of $APP_ID — re-run this script to repair it." >&2
    exit 1
fi

# The wipe makes a short copy silently fatal, so prove the mirror is exact.
expected=$(cd "$STAGE" && find . -type f | wc -l | tr -d ' ')
"${REPL[@]}" exec > "$STAGE_ROOT/count.txt" <<PY
import os
n = 0
stack = ["$APP_DIR"]
while stack:
    p = stack.pop()
    for x in os.listdir(p):
        f = p + "/" + x
        if os.stat(f)[0] & 0x4000:
            stack.append(f)
        else:
            n += 1
print("COUNT", n)
PY
actual=$(sed -n 's/^COUNT //p' "$STAGE_ROOT/count.txt" | tail -1)
if [[ "$actual" != "$expected" ]]; then
    echo "error: badge has ${actual:-?} files, source has $expected. The install was" >&2
    echo "       short — re-run this script to repair it." >&2
    exit 1
fi
echo "Verified $actual/$expected files on badge."

# ── Evict the old modules ────────────────────────────────────────────
# AppManager.execute_script only drops the *entrypoint* from sys.modules, so a
# relaunch re-imports the new foxhunt.py but its `import screen_hunt` still hits
# the previous run's cached module. Match on __file__ to catch exactly ours.
"${REPL[@]}" exec <<PY
import gc, sys
stale = [n for n, m in sys.modules.items()
         if getattr(m, "__file__", "").startswith("$APP_DIR/")]
for n in stale:
    del sys.modules[n]
gc.collect()
print("Evicted {} cached module(s): {}".format(len(stale), ", ".join(sorted(stale)) or "-"))
PY

# ── Optionally launch ────────────────────────────────────────────────
if [[ "$START" -eq 1 ]]; then
    echo "Starting $APP_ID on badge..."
    "${RUN[@]}" startapp "$APP_ID"
fi

echo "Done."
