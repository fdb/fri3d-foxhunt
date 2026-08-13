#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Migrate a badge from the OLD app package to the current one, then install
# the current app over the top.
#
#   be.fri3d.foxhunt   ->   com.enigmeta.foxhunt
#
# The package was renamed, and MicroPythonOS keys everything on the package
# id: the code lives in apps/<id>/ and the save in prefs/<id>/config.json.
# So a badge that played the old build has a full save the new build cannot
# see — same hardware, same player, same server account, different key. The
# new app finds no profile, replays onboarding, and meets its own account as
# "BADGE AL BEKEND". Nothing is corrupt; the save is simply parked under a
# name nobody reads anymore.
#
# deploy_to_badge.sh cannot do this and should not: it hardcodes one APP_ID
# and prunes only files the source dropped from within its OWN app dir. A
# second package is as far outside its scope as Breakout is. This script
# owns the rename, then hands over to it for the install.
#
# Three steps, in this order for a reason:
#   1. copy the old save to the HOST first, before anything is destroyed;
#   2. write it to the new package's prefs and verify the badge's copy byte
#      for byte, THEN delete the old prefs and the old app dir — copy first,
#      delete after, so an interrupted run always leaves a readable save;
#   3. run deploy_to_badge.sh, so the new app's first launch already finds
#      its profile and skips onboarding entirely.
#
# The save format needs no transformation. The one field that changed shape
# is hunter_id, which older builds wrote as the label "JGR-0899" instead of
# the raw number; store.py parses that back on read (see store.py, _profile)
# and rewrites it as a number the next time it saves.
#
# Usage: scripts/migrate_badge.sh [--force] [--port /dev/cu.usbmodemXXX]
#
#   --force          migrate even though the new package ALREADY has a save
#                    (it will be overwritten); also passed to the deploy
#   --port PORT      serial port (default: auto-detect /dev/cu.usbmodem*)
#
# Env overrides:
#   BADGE_PORT       same as --port

OLD_ID="be.fri3d.foxhunt"
NEW_ID="com.enigmeta.foxhunt"
BACKUP_DIR="$(pwd)/badge-backups"

FORCE=0
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=1; shift ;;
        --port)  PORT="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '5,43p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

command -v uvx >/dev/null || { echo "error: 'uvx' is required (https://docs.astral.sh/uv/)" >&2; exit 1; }

# ── Auto-detect serial port (same rules as deploy_to_badge.sh) ───────
if [[ -z "$PORT" ]]; then
    shopt -s nullglob
    ports=(/dev/cu.usbmodem* /dev/ttyACM*)
    shopt -u nullglob
    if [[ ${#ports[@]} -eq 0 ]]; then
        echo "error: no /dev/cu.usbmodem* or /dev/ttyACM* device found. Is the badge plugged in?" >&2
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

if command -v shasum >/dev/null 2>&1; then
    sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
elif command -v sha256sum >/dev/null 2>&1; then
    sha256() { sha256sum "$1" | cut -d' ' -f1; }
else
    echo "error: need shasum or sha256sum on PATH." >&2
    exit 1
fi

echo "Migrating $OLD_ID -> $NEW_ID on $PORT"
t0=$SECONDS
phase() { echo "[t+$((SECONDS - t0))s] $*"; }

MP=(uvx mpremote connect "$PORT")
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ── Survey: what does this badge actually hold? ──────────────────────
# One round trip. Returning to the launcher first is the same rule the
# deploy follows — an app whose files are about to be deleted must not be
# the one running. It is also why the survey and the delete are separate
# trips: nothing is removed until the host has the save on disk.
phase "Reading badge state..."
"${MP[@]}" exec "
from mpos import AppManager
AppManager.restart_launcher()
import os
def has(p):
    try:
        os.stat(p); return True
    except OSError:
        return False
print('OLD_APP', has('/apps/$OLD_ID'))
print('OLD_PREFS', has('/prefs/$OLD_ID/config.json'))
print('NEW_PREFS', has('/prefs/$NEW_ID/config.json'))
" | tr -d '\r' > "$WORK/state.txt"

# The badge speaks CRLF. Without the `tr` above, every value parsed as
# "True\r", which equals neither "True" nor "False" — so the survey silently
# read as "no save here", the backup was skipped and the delete ran anyway.
# Hence both halves of this: strip the CR, and refuse to continue on any
# value that is not literally True or False rather than treating a parse
# failure as "absent". (Same CRLF trap the aioREPL's read_until hit.)
state() {
    local v
    v=$(grep "^$1 " "$WORK/state.txt" | cut -d' ' -f2)
    if [[ "$v" != "True" && "$v" != "False" ]]; then
        echo "error: could not read badge state for $1 (got '$v')." >&2
        echo "       Nothing has been changed. Re-run." >&2
        exit 1
    fi
    printf '%s' "$v"
}
old_app=$(state OLD_APP)
old_prefs=$(state OLD_PREFS)
new_prefs=$(state NEW_PREFS)

# A badge with nothing to migrate is not an error — it is the second run, or
# a badge that never played the old build. Say so and fall through to the
# install, so one command covers every badge in the box.
if [[ "$old_app" == "False" && "$old_prefs" == "False" ]]; then
    phase "Nothing to migrate: no $OLD_ID app or save here."
fi

# A save already under the new package is the one thing this script must not
# quietly destroy — it means somebody already played the new build on this
# badge, and their progress is not in the old file. Only a conflict when
# there is actually an old save to write over it: on an already-migrated
# badge that save IS the migrated one, and blocking there would refuse to
# install on every badge after its first run.
if [[ "$old_prefs" == "True" && "$new_prefs" == "True" && "$FORCE" -ne 1 ]]; then
    echo "error: $NEW_ID ALREADY has a save on this badge." >&2
    echo "       Migrating would overwrite it with the old package's save," >&2
    echo "       losing whatever was played on the new build. Re-run with" >&2
    echo "       --force if the old save is really the one to keep." >&2
    exit 1
fi

# ── 1. Back the old save up to the host, before anything is destroyed ─
if [[ "$old_prefs" == "True" ]]; then
    mkdir -p "$BACKUP_DIR"
    stamp="$(date +%Y%m%d-%H%M%S)"
    backup="$BACKUP_DIR/$OLD_ID-$stamp.json"
    phase "Backing up the old save..."
    "${MP[@]}" fs cat ":/prefs/$OLD_ID/config.json" > "$backup"
    [[ -s "$backup" ]] || { echo "error: backup came back empty; refusing to continue." >&2; exit 1; }
    echo "  -> $backup ($(wc -c < "$backup" | tr -d ' ') bytes)"

    # ── 2. Copy it into the new package, and verify the badge's copy ──
    # `fs cp` exiting 0 is a claim about the transport, not proof the flash
    # holds the bytes — the same reason the deploy hashes its own install.
    phase "Writing the save under $NEW_ID..."
    "${MP[@]}" fs mkdir ":/prefs/$NEW_ID" 2>/dev/null || true
    "${MP[@]}" fs cp "$backup" ":/prefs/$NEW_ID/config.json"
    "${MP[@]}" fs cat ":/prefs/$NEW_ID/config.json" > "$WORK/verify.json"
    if [[ "$(sha256 "$backup")" != "$(sha256 "$WORK/verify.json")" ]]; then
        echo "error: the copy on the badge does not match what was sent." >&2
        echo "       Nothing was deleted; the old save is still in place and" >&2
        echo "       backed up at $backup. Re-run to retry." >&2
        exit 1
    fi
    echo "  verified $(wc -c < "$WORK/verify.json" | tr -d ' ') bytes on badge"
fi

# ── 3. Remove the old package: prefs first, then the app itself ──────
# Only now, with the save copied AND verified in its new home. LittleFS has
# no recursive unlink, so the walk is explicit — same shape the deploy uses
# to prune orphans.
#
# The gate below is not belt-and-braces, it is the lesson: the copy above is
# CONDITIONAL and this delete is not, so any reading that wrongly says "no
# old save" skips the rescue and destroys the original anyway. Ask the badge
# itself, immediately before destroying anything, and make the answer the
# permission — never a variable computed a dozen lines earlier.
if [[ "$old_prefs" == "True" ]]; then
    landed=$("${MP[@]}" exec "
import os
try:
    print(os.stat('/prefs/$NEW_ID/config.json')[6])
except OSError:
    print(0)
" | tr -d '\r')
    if [[ "$landed" -lt 1 ]]; then
        echo "error: $NEW_ID has no save on the badge, so the old one is still" >&2
        echo "       the only copy — refusing to delete it. Backup: $backup" >&2
        exit 1
    fi
fi

if [[ "$old_app" == "True" || "$old_prefs" == "True" ]]; then
phase "Removing $OLD_ID..."
"${MP[@]}" exec "
import os
def rmtree(p):
    try:
        entries = os.listdir(p)
    except OSError:
        return 0
    n = 0
    for name in entries:
        f = p + '/' + name
        if os.stat(f)[0] & 0x4000:
            n += rmtree(f)
        else:
            os.remove(f); n += 1
    os.rmdir(p)
    return n
print('removed', rmtree('/prefs/$OLD_ID'), 'pref file(s)')
print('removed', rmtree('/apps/$OLD_ID'), 'app file(s)')
"
fi

# ── 4. Install the current app ───────────────────────────────────────
# Hand over rather than reimplement: the deploy owns precompiling, the
# provenance stamp, the manifest and the sys.modules eviction.
phase "Installing $NEW_ID..."
deploy=(scripts/deploy_to_badge.sh --start --port "$PORT")
if [[ "$FORCE" -eq 1 ]]; then
    deploy+=(--force)
fi
"${deploy[@]}"

phase "Migration complete."
echo
echo "The player's profile, catches, voorraad and vrienden moved across."
echo "Their dossier's zelf-gevonden stamps come from the server, not the"
echo "save, so they reappear on the next resync."
