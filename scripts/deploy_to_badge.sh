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
#   2. deletes the files the source no longer has, and only those (mpremote
#      never deletes, so orphans pile up until LittleFS is full; it *does* skip
#      files that are unchanged, which is what keeps a deploy near 40s);
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

# ── Stop the app, and hash what the badge currently holds ────────────
# All in one round trip: each REPL call costs ~4s of interpreter start and
# serial handshake, which is a real slice of the deploy budget.
# Overwriting the files under a live activity leaves it running old code with
# new code on disk. Stop it first; onDestroy also lets the app drop its timers.
# Hashing all 71 files here takes ~20s, against ~37s for `mpremote fs cp -r` to
# hash them one REPL round trip at a time — and it lets us hand the copy a stage
# holding only what actually changed, which is the difference between a ~95s
# deploy and a ~45s one. 16 hex digits of SHA-256 is far past collision risk for
# a set this size.
echo "Returning badge to launcher..."
wake_repl
"${REPL[@]}" exec > "$STAGE_ROOT/remote.txt" <<PY
from mpos import AppManager
AppManager.restart_launcher()
import binascii, hashlib, os
root = "$APP_DIR"
buf = bytearray(1024)
mv = memoryview(buf)
stack = [root]
while stack:
    p = stack.pop()
    try:
        names = os.listdir(p)
    except OSError:
        continue
    for n in names:
        f = p + "/" + n
        if os.stat(f)[0] & 0x4000:
            stack.append(f)
            continue
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            while True:
                k = fh.readinto(buf)
                if not k:
                    break
                h.update(mv[:k])
        print("F", binascii.hexlify(h.digest()).decode()[:16], f[len(root) + 1:])
PY

# ── Work out what actually differs ───────────────────────────────────
# The REPL speaks CRLF, so strip the \r or every path fails to match its twin.
# That is what broke an earlier version of this diff: it compared
# "assets/art.py\r" against "assets/art.py" and called all 71 files orphans.
# comm compares whole lines, so both .sha files must be sorted as whole lines --
# sorting them by path instead silently mismatches neighbours (it reported
# store.py as changed whenever sound.py was, they being adjacent).
tr -d '\r' < "$STAGE_ROOT/remote.txt" | sed -n 's/^F //p' | sort > "$STAGE_ROOT/remote.sha"
cut -d' ' -f2- "$STAGE_ROOT/remote.sha" | sort > "$STAGE_ROOT/remote.lst"
(cd "$STAGE" && find . -type f) | sed 's|^\./||' | sort > "$STAGE_ROOT/stage.lst"
# Same digest, same truncation, so the two sides are directly comparable.
(cd "$STAGE" && while IFS= read -r f; do
    printf '%s %s\n' "$(shasum -a 256 "$f" | cut -c1-16)" "$f"
done < "$STAGE_ROOT/stage.lst") | sort > "$STAGE_ROOT/stage.sha"

# On the badge but no longer in the source.
comm -23 "$STAGE_ROOT/remote.lst" "$STAGE_ROOT/stage.lst" > "$STAGE_ROOT/orphans.lst"
# In the source but missing or different on the badge. Comparing whole
# "<sha> <path>" lines catches both cases in one pass: a changed file has no
# matching line, and a missing one has no line at all.
comm -23 "$STAGE_ROOT/stage.sha" "$STAGE_ROOT/remote.sha" | cut -d' ' -f2- \
    | sort > "$STAGE_ROOT/changed.lst"

if [[ -s "$STAGE_ROOT/orphans.lst" ]]; then
    echo "Pruning $(wc -l < "$STAGE_ROOT/orphans.lst" | tr -d ' ') stale file(s) on badge:"
    sed 's/^/  - /' "$STAGE_ROOT/orphans.lst"
    # In batches: paste mode echoes every byte back while LVGL still holds the
    # CPU, so a payload of more than roughly 20 lines stalls on flow control and
    # trips the controller's 1s write timeout.
    split -l 15 "$STAGE_ROOT/orphans.lst" "$STAGE_ROOT/batch."
    for batch in "$STAGE_ROOT"/batch.*; do
        {
            echo "import os"
            echo "for p in ("
            sed 's|.*|    "&",|' "$batch"
            echo "):"
            echo "    try:"
            echo "        os.remove(\"$APP_DIR/\" + p)"
            echo "    except OSError as e:"
            echo "        print(\"could not remove\", p, e)"
        } | "${REPL[@]}" exec
    done
    # Deepest-first, so a directory is only tried once its children are gone.
    # rmdir refuses a non-empty one, which is exactly the guard we want.
    "${REPL[@]}" exec <<PY
import os
dirs = []
stack = ["$APP_DIR"]
while stack:
    p = stack.pop()
    for n in os.listdir(p):
        f = p + "/" + n
        if os.stat(f)[0] & 0x4000:
            dirs.append(f)
            stack.append(f)
for d in sorted(dirs, key=len, reverse=True):
    try:
        os.rmdir(d)
    except OSError:
        pass
s = os.statvfs("/")
print("{} bytes now free".format(s[0] * s[3]))
PY
fi

# ── Install just the difference ──────────────────────────────────────
# installapp runs `mpremote fs cp -r <dir> :/apps/`, and that merges rather than
# replaces — so handing it a tree holding only the changed files updates exactly
# those and leaves the rest alone. Left to copy the whole stage it would re-hash
# all 71 files over the wire, which is the single most expensive thing a deploy
# can do. Everything else still happens: the copy makes any missing directories,
# and installapp refreshes AppManager afterwards so a changed manifest lands.
# It retries because mpremote's raw-REPL handshake sometimes times out with
# "timeout waiting for first EOF reception" when the badge is busy.
changed_count=$(wc -l < "$STAGE_ROOT/changed.lst" | tr -d ' ')
installed=1
if [[ "$changed_count" -eq 0 ]]; then
    echo "No file changed; badge is already up to date."
else
    echo "Copying $changed_count changed file(s):"
    sed 's/^/  + /' "$STAGE_ROOT/changed.lst"
    DELTA="$STAGE_ROOT/delta/$APP_ID"
    while IFS= read -r f; do
        mkdir -p "$DELTA/$(dirname "$f")"
        cp "$STAGE/$f" "$DELTA/$f"
    done < "$STAGE_ROOT/changed.lst"
    installed=0
    for attempt in 1 2 3; do
        if "${RUN[@]}" installapp "$DELTA"; then
            installed=1
            break
        fi
        echo "install attempt $attempt/3 failed; letting the badge settle..." >&2
        sleep 5
        wake_repl
    done
fi
if [[ "$installed" -ne 1 ]]; then
    echo "error: install failed three times. The badge keeps the previous copy of" >&2
    echo "       $APP_ID, minus any file this run pruned — re-run to repair it." >&2
    exit 1
fi

# ── Verify, evict the old modules, and launch ────────────────────────
# All three in one round trip. The badge does the count check itself so it can
# refuse to launch a short install without a second trip back to ask.
# The eviction is the actual restart fix — AppManager.execute_script only drops
# the *entrypoint* from sys.modules, so a relaunch re-imports the new foxhunt.py
# while its `import screen_hunt` still hits the previous run's cached module.
# Match on __file__ to catch exactly ours, whatever they are named.
expected=$(cd "$STAGE" && find . -type f | wc -l | tr -d ' ')
"${REPL[@]}" exec > "$STAGE_ROOT/verify.txt" <<PY
import gc, os, sys
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
stale = [k for k, m in sys.modules.items()
         if getattr(m, "__file__", "").startswith("$APP_DIR/")]
for k in stale:
    del sys.modules[k]
gc.collect()
print("EVICTED", len(stale), ",".join(sorted(stale)))
if $START and n == $expected:
    from mpos import AppManager
    AppManager.start_app("$APP_ID")
    print("STARTED")
PY
tr -d '\r' < "$STAGE_ROOT/verify.txt" > "$STAGE_ROOT/verify.lst"
actual=$(sed -n 's/^COUNT //p' "$STAGE_ROOT/verify.lst" | tail -1)
if [[ "$actual" != "$expected" ]]; then
    echo "error: badge has ${actual:-?} files, source has $expected. The install was" >&2
    echo "       short — re-run this script to repair it." >&2
    exit 1
fi
echo "Verified $actual/$expected files on badge."
sed -n 's/^EVICTED /Evicted cached modules: /p' "$STAGE_ROOT/verify.lst"
if [[ "$START" -eq 1 ]]; then
    grep -q '^STARTED' "$STAGE_ROOT/verify.lst" \
        || { echo "error: app did not start on badge." >&2; exit 1; }
    echo "Started $APP_ID on badge."
fi

echo "Done."
