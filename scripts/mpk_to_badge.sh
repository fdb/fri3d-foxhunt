#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Install a built .mpk onto a USB-connected badge THE WAY THE APP STORE DOES,
# so the artifact we are about to publish is the artifact that got tested.
#
# This is not the same test as scripts/deploy_to_badge.sh. The deploy pushes a
# staged tree file by file, at -O2, and never builds or opens a package; a
# store install streams one zip into MicroPythonOS's own StreamingUnzip, at
# -O3, after rmtree-ing the app dir. Those are different bytes down a
# different path, so "the deploy works" says nothing about whether the .mpk
# installs. This runs the real one:
#
#   * the same StreamingUnzip the store feeds, with the same
#     expected_app_name, so the MPK spec check (exactly one top-level dir,
#     named for the app) is enforced against our zip and not just assumed;
#   * the same free-space guard (AppManager._check_free_space);
#   * the same shutil.rmtree of apps/<fullname> first, so an install is a
#     clean replace and lingering files from a USB deploy cannot flatter it.
#
# What it does NOT exercise is DownloadManager.download_url — the HTTP leg.
# The badge is on the terrain's isolated SSID and cannot reach a laptop, so
# the bytes arrive over USB instead. That leg is generic OS code and carries
# nothing app-specific; everything the PACKAGE can get wrong (layout, top-level
# dir, compression method, truncation, size) is downstream of it and is tested
# here. Serve the file over HTTP and use the store itself if you ever need the
# download leg covered too.
#
# SAVE DATA SURVIVES, deliberately. Prefs live in prefs/<fullname>/, outside
# the app dir this replaces, so running this on a badge with a profile is also
# the upgrade test: the player must come back with their name and their
# catches. Use scripts/delete_account.sh / ALLES WISSEN to start clean.
#
# Usage: scripts/mpk_to_badge.sh [--mpk PATH] [--port /dev/cu.usbmodemXXX]
#
#   --mpk PATH       package to install (default: dist/<fullname>_<version>.mpk
#                    for the version in META-INF/MANIFEST.JSON)
#   --port PORT      serial port (default: auto-detect /dev/cu.usbmodem*)
#
# Env overrides:
#   BADGE_PORT       same as --port

APP_DIR_SRC="com.enigmeta.foxhunt"
MANIFEST="$APP_DIR_SRC/META-INF/MANIFEST.JSON"

MPK=""
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mpk)   MPK="${2:-}"; shift 2 ;;
        --port)  PORT="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '5,45p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

command -v uvx >/dev/null || { echo "error: 'uvx' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }
command -v unzip >/dev/null || { echo "error: 'unzip' is required" >&2; exit 1; }
[[ -f "$MANIFEST" ]] || { echo "error: missing $MANIFEST" >&2; exit 1; }

APP_ID=$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['fullname'])")
VERSION=$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['version'])")
[[ -n "$MPK" ]] || MPK="dist/${APP_ID}_${VERSION}.mpk"
[[ -f "$MPK" ]] || { echo "error: package not found: $MPK (run scripts/build_mpk.sh)" >&2; exit 1; }

# ── Auto-detect serial port (same rules as deploy_to_badge.sh) ───────
if [[ -z "$PORT" ]]; then
    shopt -s nullglob
    ports=(/dev/cu.usbmodem* /dev/ttyACM*)
    shopt -u nullglob
    if [[ ${#ports[@]} -eq 0 ]]; then
        echo "error: no /dev/cu.usbmodem* or /dev/ttyACM* device found. Is the badge plugged in?" >&2
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

# ── Check the package HOST-side, before the badge is touched ─────────
# The badge enforces all of this too, but it enforces it halfway through an
# install that has already deleted the working app. Failing here costs
# nothing; failing there leaves the badge with no app at all.
unzip -tq "$MPK" >/dev/null || { echo "error: $MPK is not a readable zip" >&2; exit 1; }
tops=$(unzip -Z1 "$MPK" | cut -d/ -f1 | sort -u)
if [[ "$tops" != "$APP_ID" ]]; then
    echo "error: $MPK must hold exactly one top-level dir named '$APP_ID'." >&2
    echo "       Found: $(echo "$tops" | tr '\n' ' ')" >&2
    echo "       The badge's StreamingUnzip refuses anything else." >&2
    exit 1
fi

size=$(wc -c < "$MPK" | tr -d ' ')
echo "Installing $MPK ($size bytes) as $APP_ID $VERSION -> $PORT"
t0=$SECONDS
phase() { echo "[t+$((SECONDS - t0))s] $*"; }

MP=(uvx mpremote connect "$PORT")
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REMOTE_MPK="/_install.mpk"

# ── Return to the launcher and drop the app's modules ────────────────
# Same two reasons as the deploy: no activity may hold the code about to be
# deleted, and MicroPythonOS keeps one interpreter, so modules cached from
# the previous build would outlive the files and serve their old code to the
# next launch.
phase "Returning to launcher, evicting cached modules..."
"${MP[@]}" exec "
from mpos import AppManager
AppManager.restart_launcher()
import sys
gone = [n for n, m in sys.modules.items()
        if '$APP_ID' in str(getattr(m, '__file__', ''))]
for n in gone:
    del sys.modules[n]
print('evicted', len(gone), 'module(s)')
" | tr -d '\r'

# ── Push the package, then extract it on-badge ───────────────────────
phase "Copying package to badge..."
"${MP[@]}" fs cp "$MPK" ":$REMOTE_MPK" >/dev/null

# A blocking, self-contained script rather than a chain of execs: the OS loop
# is idle at the launcher, nothing needs to render, and one import keeps the
# whole install inside a single raw-REPL round trip. The app dir is removed
# only AFTER the package is safely on flash, and the package is removed as
# soon as it is extracted, so peak free-space demand stays as low as it can.
cat > "$WORK/_mpk_install.py" <<PY
import json, os, shutil
from mpos import AppManager
from mpos.content.streaming_unzip import StreamingUnzip

APP = "$APP_ID"
SRC = "$REMOTE_MPK"
dest = "apps/" + APP

st = os.statvfs("/")
print("free before:", st[0] * st[4] // 1024, "KB")

try:
    shutil.rmtree(dest)
    print("removed existing", dest)
except OSError:
    print("no existing", dest)

ex = StreamingUnzip(
    dest,
    expected_app_name=APP,
    free_space_limit=lambda req: AppManager._check_free_space(".", req),
)
n = 0
with open(SRC, "rb") as fh:
    while True:
        chunk = fh.read(4096)
        if not chunk:
            break
        ex.feed(chunk)
        n += len(chunk)
ex.finish()
print("fed", n, "bytes")

os.remove(SRC)

# Report what actually landed, from the badge's own filesystem.
# Hand-rolled recursion: MicroPython's os has no walk().
def count_files(p):
    n = 0
    for name in os.listdir(p):
        f = p + "/" + name
        if os.stat(f)[0] & 0x4000:
            n += count_files(f)
        else:
            n += 1
    return n

print("installed files:", count_files(dest))
with open(dest + "/META-INF/MANIFEST.JSON") as fh:
    m = json.load(fh)
print("installed version:", m["version"], m["fullname"])
AppManager.refresh_apps()
st = os.statvfs("/")
print("free after:", st[0] * st[4] // 1024, "KB")
print("INSTALL_OK")
PY

phase "Extracting through the store's StreamingUnzip..."
"${MP[@]}" fs cp "$WORK/_mpk_install.py" :/_mpk_install.py >/dev/null
"${MP[@]}" exec "import _mpk_install" | tr -d '\r' | tee "$WORK/out.txt"
"${MP[@]}" fs rm :/_mpk_install.py >/dev/null 2>&1 || true

grep -q INSTALL_OK "$WORK/out.txt" || { echo "error: install did not complete." >&2; exit 1; }

phase "Done. Open $APP_ID from the badge's launcher."

# There is deliberately no --start. AppManager.start_app runs on the
# asyncio/LVGL loop, and firing it from an exec wedged a badge hard enough to
# need a power-cycle ("could not enter raw repl"). The deploy can afford it
# because it is already deep in a raw-REPL session it controls; here the last
# thing the script does is hand the badge back to a human, and a launcher tap
# costs nothing. A store install ends at the launcher too, so this is also
# what the tested path actually looks like.
