#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Give a USB-connected badge its startbeest — the catch-up path for test
# badges whose account predates the grant-at-registration feature.
#
# The pick is NOT random per run: it is the same deterministic per-badge
# creature the server mints at registration (FNV-1a over the badge id — see
# server/src/lib/starter.ts and creatures.starter_for), so re-running the
# script can never reroll it. The grant lands in BOTH places a creature must
# live: the server's players_creatures (via POST /api/v1/auth/starter, which
# only ever grants to an EMPTY roster) and the badge's local store (over
# mpremote's raw REPL, same transport as deploy_to_badge.sh).
#
# It refuses unless BOTH rosters are empty:
#   * local catches would mean this badge is already mid-game;
#   * server catches would mean the badge should RESTORE, not be re-seeded.
#
# Usage: scripts/get_random_creature.sh [--port /dev/cu.usbmodemXXX] [--server URL]
#
# Env overrides:
#   BADGE_PORT       same as --port
#   FOXHUNT_SERVER   same as --server (default: the deployed worker)

APP_ID="com.enigmeta.foxhunt"
SERVER="${FOXHUNT_SERVER:-https://foxhunt.enigmeta.workers.dev}"
PORT="${BADGE_PORT:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)   PORT="${2:-}"; shift 2 ;;
        --server) SERVER="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '5,24p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

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

MP=(uvx mpremote connect "$PORT")

# ── 1. Ask the badge who it is and what it already has ───────────────
# The app's own modules answer (store reads the same SharedPreferences the
# game writes), so there is no second opinion about what "the roster" is.
# The OS keeps running across raw-REPL execs; sentinel line, not $?, is the
# verdict (the REPL folds exceptions into output).
echo "Reading badge state on $PORT..."
state="$("${MP[@]}" exec "
import sys, machine
sys.path.insert(0, '/apps/$APP_ID/assets')
import store
badge = ':'.join('%02X' % b for b in machine.unique_id())
p = store.profile() or {}
print('STATE', badge, ','.join(str(i) for i in store.caught_ids()) or '-',
      'synced' if p.get('synced') else 'unsynced')
" 2>&1)" || { echo "error: badge did not answer; device said:" >&2
              echo "$state" >&2; exit 1; }

case "$state" in
    *"STATE "*) ;;
    *) echo "error: badge did not report its state; device said:" >&2
       echo "$state" >&2; exit 1 ;;
esac
# Two fields, not three: the `##*STATE ` above already ate the sentinel. And
# the serial REPL ends every line with CR, which `read` leaves on the LAST
# field (a non-whitespace IFS char delimits, it does not get trimmed) — so an
# empty roster arrives as "-\r" and the emptiness check below fails on a badge
# that has nothing. Drop the CRs before parsing.
state="${state//$'\r'/}"
read -r badge caught synced <<< "${state##*STATE }"
echo "  badge $badge"

if [[ "$caught" != "-" ]]; then
    echo "error: local roster is not empty (creatures: $caught)." >&2
    echo "       The startbeest is only for a badge that has nothing yet." >&2
    exit 1
fi

# ── 2. Ask the server to grant the startbeest ────────────────────────
# The server re-checks emptiness against ITS roster and refuses otherwise —
# a 409 here means the account has server-side catches this badge lost, and
# the right fix is a restore in the app, not a fresh seed.
echo "Requesting startbeest from $SERVER..."
resp="$(curl -sS -w $'\n%{http_code}' -X POST "$SERVER/api/v1/auth/starter" \
        -H 'Content-Type: application/json' \
        -d "{\"badge_id\": \"$badge\"}")"
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"

case "$code" in
    200) ;;
    404) echo "error: the server does not know this badge ($body)." >&2
         if [[ "$synced" == "synced" ]]; then
             # The badge says it registered and the server has never heard of
             # it. That combination is a profile written by FakeRegistrar (or
             # against a local wrangler DB): nothing ever left the badge. A
             # hunter_id in that profile is the giveaway — the real transport
             # skips the bridge leg, so it can only ever store None.
             echo "       The badge claims 'synced', so this profile was written" >&2
             echo "       offline (FakeRegistrar) or against a local server —" >&2
             echo "       it never reached $SERVER." >&2
         fi
         echo "       Register on the badge first — registration now grants" >&2
         echo "       the startbeest by itself." >&2
         exit 1 ;;
    409) echo "error: the server roster is not empty ($body)." >&2
         echo "       Use 'Herstel mijn account' on the badge instead." >&2
         exit 1 ;;
    *)   echo "error: server said HTTP $code: $body" >&2; exit 1 ;;
esac

starter="$(printf '%s' "$body" | grep -o '"starter":[0-9]*' | head -1 | cut -d: -f2)"
[[ -n "$starter" ]] || { echo "error: no starter id in server reply: $body" >&2; exit 1; }

# ── 3. Land it in the badge's local store ────────────────────────────
out="$("${MP[@]}" exec "
import sys
sys.path.insert(0, '/apps/$APP_ID/assets')
import store
from creatures import by_id
store.add_caught($starter, origin='start')
print('GRANTED', by_id($starter)['naam'])
" 2>&1)"

case "$out" in
    *"GRANTED "*)
        naam="${out##*GRANTED }"
        echo "Startbeest granted: ${naam%%[$'\r\n']*} (id $starter) — server + badge." ;;
    *)  echo "error: server granted id $starter but the badge write failed:" >&2
        echo "$out" >&2
        echo "       Re-running the script is safe (the grant is idempotent)." >&2
        exit 1 ;;
esac
