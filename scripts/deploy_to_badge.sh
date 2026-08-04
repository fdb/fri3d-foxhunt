#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Deploy the Foxhunt app onto a USB-connected Fri3d badge running
# MicroPythonOS. Apps are plain files on the device's LittleFS, so this does
# NOT touch firmware — it stages a badge-clean copy (desktop cruft dropped)
# and pushes only what differs, over mpremote's raw REPL.
#
# Installing over a *running* app is not enough on its own, so this also:
#   1. returns the badge to the launcher, so no activity holds the old code;
#   2. deletes the files the source no longer has, and only those (a plain
#      copy never deletes, so orphans pile up until LittleFS is full);
#   3. drops the app's modules from sys.modules, so the next launch re-imports
#      from disk instead of reusing the previous run's cached modules.
#
# Everything badge-side rides mpremote's raw REPL, NOT the aioREPL that
# scripts/mpos_controller.py speaks. The aioREPL echoes every pasted byte
# back while LVGL starves the reader — ~115 B/s measured, and a payload past
# ~2.5KB fills the badge's input buffer and dies on a write timeout. Raw
# REPL has no echo: the same state walk that cost 16s through the controller
# runs in under 4. The OS keeps running across raw-REPL execs (same
# interpreter, AppManager and sys.modules included), so the controller's
# emulator/aioREPL workflow is untouched — it is just the wrong transport
# for bulk deploy traffic.
#
# Usage: scripts/deploy_to_badge.sh [--start] [--port /dev/cu.usbmodemXXX]
#
#   --start          launch the app on the badge after installing
#   --port PORT      serial port (default: auto-detect /dev/cu.usbmodem*)
#
# Env overrides:
#   BADGE_PORT       same as --port

PROJECT_DIR="$(pwd)"
APP_ID="be.fri3d.foxhunt"
APP_SRC="$PROJECT_DIR/$APP_ID"

START=0
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start) START=1; shift ;;
        --port)  PORT="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '5,33p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

# ── Sanity checks ────────────────────────────────────────────────────
[[ -d "$APP_SRC" ]] || { echo "error: app dir not found: $APP_SRC" >&2; exit 1; }
command -v uvx >/dev/null || { echo "error: 'uvx' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

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

# ── Stage a badge-clean copy ─────────────────────────────────────────
STAGE_ROOT="$(mktemp -d)"
trap 'rm -rf "$STAGE_ROOT"' EXIT
STAGE="$STAGE_ROOT/$APP_ID"

cp -R "$APP_SRC" "$STAGE"
# Desktop-only cruft: CPython bytecode caches and Finder metadata.
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '.DS_Store' -delete

echo "Deploying $APP_ID -> $PORT"

# Every phase prints its elapsed time: the deploy is a serial-port pipeline
# whose cost lives in places invisible from the outside (REPL handshakes,
# on-badge stat walks), so without these numbers a regression is
# undiagnosable — a 7-minute deploy looks exactly like a 1-minute one.
t0=$SECONDS
phase() { echo "[t+$((SECONDS - t0))s] $*"; }

MP=(uvx mpremote connect "$PORT")
APP_DIR="apps/$APP_ID"

# ── Stop the app, and learn what the badge currently holds ───────────
# One round trip: stop the app first (overwriting files under a live activity
# leaves it running old code with new code on disk; onDestroy also lets it
# drop its timers), then report per-file state.
#
# The badge's state normally comes from .deploy.sha, a manifest this script
# ships inside the app dir with every install ("sha16 size path" per line).
# Hashing every file costs ~0.28s apiece of open() overhead; reading one
# manifest costs one. The manifest is only TRUSTED after a stat walk proves
# it: exactly the same paths on disk, every size matching. That check is what
# makes it safe against every way the manifest can lie — an interrupted
# install truncates a file (size differs), a pruned orphan lingers in the
# lines (path gone), a store install rmtrees the dir (manifest gone too,
# which is why it lives *inside* the app dir). Any doubt → full hash walk,
# same "F <sha16> <path>" output either way. 16 hex digits of SHA-256 is far
# past collision risk for a set this size.
phase "Reading badge state..."
cat > "$STAGE_ROOT/exec1.py" <<PY
from mpos import AppManager
AppManager.restart_launcher()
import binascii, hashlib, os
root = "$APP_DIR"
man = {}
try:
    with open(root + "/.deploy.sha") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) == 3:
                man[parts[2]] = (parts[0], int(parts[1]))
except OSError:
    pass
disk = {}
stack = [root]
while stack:
    p = stack.pop()
    try:
        names = os.listdir(p)
    except OSError:
        continue
    for n in names:
        f = p + "/" + n
        st = os.stat(f)
        if st[0] & 0x4000:
            stack.append(f)
        else:
            rel = f[len(root) + 1:]
            if rel != ".deploy.sha":
                disk[rel] = st[6]
ok = bool(man) and len(man) == len(disk)
ok = ok and all(r in disk and man[r][1] == disk[r] for r in man)
print("MAN", "ok" if ok else "stale")
if ok:
    for r in man:
        print("F", man[r][0], r)
else:
    buf = bytearray(1024)
    mv = memoryview(buf)
    for r in disk:
        h = hashlib.sha256()
        with open(root + "/" + r, "rb") as fh:
            while True:
                k = fh.readinto(buf)
                if not k:
                    break
                h.update(mv[:k])
        print("F", binascii.hexlify(h.digest()).decode()[:16], r)
PY
"${MP[@]}" run "$STAGE_ROOT/exec1.py" > "$STAGE_ROOT/remote.txt"

# ── Work out what actually differs ───────────────────────────────────
# The REPL speaks CRLF, so strip the \r or every path fails to match its twin.
# That is what broke an earlier version of this diff: it compared
# "assets/art.py\r" against "assets/art.py" and called all 71 files orphans.
# comm compares whole lines, so both .sha files must be sorted as whole lines --
# sorting them by path instead silently mismatches neighbours (it reported
# store.py as changed whenever sound.py was, they being adjacent).
tr -d '\r' < "$STAGE_ROOT/remote.txt" > "$STAGE_ROOT/remote.clean"
man_state=$(sed -n 's/^MAN //p' "$STAGE_ROOT/remote.clean" | tail -1)
sed -n 's/^F //p' "$STAGE_ROOT/remote.clean" | sort > "$STAGE_ROOT/remote.sha"
cut -d' ' -f2- "$STAGE_ROOT/remote.sha" | sort > "$STAGE_ROOT/remote.lst"
(cd "$STAGE" && find . -type f) | sed 's|^\./||' | sort > "$STAGE_ROOT/stage.lst"
# The stage manifest is both halves of the scheme: its "sha path" columns are
# this run's side of the diff, and shipped whole as .deploy.sha it is what the
# NEXT run's stat walk validates instead of hashing. Same digest, same
# truncation, so the two sides are directly comparable.
(cd "$STAGE" && while IFS= read -r f; do
    printf '%s %s %s\n' "$(shasum -a 256 "$f" | cut -c1-16)" \
        "$(stat -f%z "$f")" "$f"
done < "$STAGE_ROOT/stage.lst") > "$STAGE_ROOT/stage.man"
awk '{print $1, $3}' "$STAGE_ROOT/stage.man" | sort > "$STAGE_ROOT/stage.sha"

# On the badge but no longer in the source.
comm -23 "$STAGE_ROOT/remote.lst" "$STAGE_ROOT/stage.lst" > "$STAGE_ROOT/orphans.lst"
# In the source but missing or different on the badge. Comparing whole
# "<sha> <path>" lines catches both cases in one pass: a changed file has no
# matching line, and a missing one has no line at all.
comm -23 "$STAGE_ROOT/stage.sha" "$STAGE_ROOT/remote.sha" | cut -d' ' -f2- \
    | sort > "$STAGE_ROOT/changed.lst"
changed_count=$(wc -l < "$STAGE_ROOT/changed.lst" | tr -d ' ')
orphan_count=$(wc -l < "$STAGE_ROOT/orphans.lst" | tr -d ' ')

# Nothing to copy, nothing to prune, manifest already proven by the stat walk:
# the whole deploy was one REPL trip. (--start still needs the second trip.)
if [[ "$changed_count" -eq 0 && "$orphan_count" -eq 0 \
      && "$man_state" == "ok" && "$START" -ne 1 ]]; then
    phase "No file changed; badge is already up to date."
    phase "Done."
    exit 0
fi

# ── Install just the difference ──────────────────────────────────────
# `mpremote fs cp -r` merges rather than replaces — handing it a tree holding
# only the changed files updates exactly those and leaves the rest alone. The
# delta always carries a fresh .deploy.sha: on an orphan-only or
# stale-manifest run that is the entire delta, and pushing it BEFORE the
# prune below is deliberate — if this deploy dies in between, the manifest
# names files the disk still holds, the next run's stat walk sees the
# mismatch and falls back to hashing. Stale manifests self-heal; a missing
# one (store install rmtree'd the dir) just means one slow first deploy.
# It retries because mpremote's raw-REPL handshake sometimes times out when
# the badge is busy.
need_install=0
[[ "$changed_count" -gt 0 || "$orphan_count" -gt 0 || "$man_state" != "ok" ]] && need_install=1
installed=1
if [[ "$need_install" -eq 1 ]]; then
    if [[ "$changed_count" -gt 0 ]]; then
        phase "Copying $changed_count changed file(s) + manifest:"
        sed 's/^/  + /' "$STAGE_ROOT/changed.lst"
    else
        phase "Refreshing manifest..."
    fi
    DELTA="$STAGE_ROOT/delta/$APP_ID"
    mkdir -p "$DELTA"
    while IFS= read -r f; do
        mkdir -p "$DELTA/$(dirname "$f")"
        cp "$STAGE/$f" "$DELTA/$f"
    done < "$STAGE_ROOT/changed.lst"
    cp "$STAGE_ROOT/stage.man" "$DELTA/.deploy.sha"
    installed=0
    for attempt in 1 2 3; do
        if "${MP[@]}" fs cp -r "$DELTA" :/apps/ >/dev/null; then
            installed=1
            break
        fi
        echo "install attempt $attempt/3 failed; letting the badge settle..." >&2
        sleep 5
    done
fi
if [[ "$installed" -ne 1 ]]; then
    echo "error: install failed three times. The badge keeps the previous copy of" >&2
    echo "       $APP_ID — re-run to repair it." >&2
    exit 1
fi

# ── Prune, verify, refresh, evict the old modules, and launch ────────
# All of it in one round trip. Orphans are deleted here, after the install,
# so the freshly pushed manifest already describes the pruned tree.
# The badge does the count check itself so it can refuse to launch a short
# install without a second trip back to ask; the count skips .deploy.sha,
# which is deploy bookkeeping, not part of the app.
# refresh_apps makes AppManager re-read the manifests (what the controller's
# installapp did as a separate call).
# The eviction is the actual restart fix — AppManager.execute_script only drops
# the *entrypoint* from sys.modules, so a relaunch re-imports the new foxhunt.py
# while its `import screen_hunt` still hits the previous run's cached module.
# Match on __file__ to catch exactly ours, whatever they are named.
expected=$(cd "$STAGE" && find . -type f | wc -l | tr -d ' ')
if [[ "$orphan_count" -gt 0 ]]; then
    phase "Pruning $orphan_count stale file(s), verifying + evicting..."
    sed 's/^/  - /' "$STAGE_ROOT/orphans.lst"
else
    phase "Install done; verifying + evicting..."
fi
{
    echo "import gc, os, sys"
    echo "root = \"$APP_DIR\""
    echo "orphans = ["
    sed 's|.*|    "&",|' "$STAGE_ROOT/orphans.lst"
    echo "]"
    cat <<PY
for p in orphans:
    try:
        os.remove(root + "/" + p)
    except OSError as e:
        print("could not remove", p, e)
if orphans:
    # Deepest-first, so a directory is only tried once its children are
    # gone. rmdir refuses a non-empty one, which is exactly the guard we
    # want.
    dirs = []
    stack = [root]
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
n = 0
stack = [root]
while stack:
    p = stack.pop()
    for x in os.listdir(p):
        f = p + "/" + x
        if os.stat(f)[0] & 0x4000:
            stack.append(f)
        elif f != root + "/.deploy.sha":
            n += 1
print("COUNT", n)
from mpos import AppManager
if $need_install:
    # only after a real install: re-reads every app's manifest, ~10s
    AppManager.refresh_apps()
stale = [k for k, m in sys.modules.items()
         if getattr(m, "__file__", "").startswith(root + "/")]
for k in stale:
    del sys.modules[k]
gc.collect()
print("EVICTED", len(stale), ",".join(sorted(stale)))
if $START and n == $expected:
    AppManager.start_app("$APP_ID")
    print("STARTED")
PY
} > "$STAGE_ROOT/exec2.py"
"${MP[@]}" run "$STAGE_ROOT/exec2.py" > "$STAGE_ROOT/verify.txt"
tr -d '\r' < "$STAGE_ROOT/verify.txt" > "$STAGE_ROOT/verify.lst"
actual=$(sed -n 's/^COUNT //p' "$STAGE_ROOT/verify.lst" | tail -1)
if [[ "$actual" != "$expected" ]]; then
    echo "error: badge has ${actual:-?} files, source has $expected. The install was" >&2
    echo "       short — re-run this script to repair it." >&2
    exit 1
fi
phase "Verified $actual/$expected files on badge."
sed -n 's/^EVICTED /Evicted cached modules: /p' "$STAGE_ROOT/verify.lst"
if [[ "$START" -eq 1 ]]; then
    grep -q '^STARTED' "$STAGE_ROOT/verify.lst" \
        || { echo "error: app did not start on badge." >&2; exit 1; }
    echo "Started $APP_ID on badge."
fi

phase "Done."
