#!/usr/bin/env bash
# Wipe one player's account off a foxhunt server, from a laptop.
#
# The badge can already do this to itself (instellingen -> ALLES WISSEN), but
# only while it still holds the account. Anything that breaks that pairing
# leaves a row nobody can reach: a badge wiped locally, a badge that died, an
# emulator whose profile was thrown away. The account lives on, and the next
# registration on that hardware meets it as "BADGE AL BEKEND" forever.
#
# The emulator is the everyday case. Its badge_id is a FIXED fake MAC
# (registrar.badge_id, "A4:CF:12:9B:03:7E") shared by every desktop run, so a
# throwaway test profile still registers a real, permanent account on whichever
# server the app points at -- prod, by default.
#
# It calls DELETE /api/v1/auth/user, the same route ALLES WISSEN calls, rather
# than touching D1. One definition of what deleting means: soft (dt_deleted
# stamped, row kept, an organiser can undo it by clearing the column), logged
# to game_events, and idempotent. See CLAUDE.md, "ALLES WISSEN is the only real
# way to start over".
#
# Usage:
#   scripts/delete_account.sh                     # list accounts, delete nothing
#   scripts/delete_account.sh BOBBY               # by name (case-insensitive)
#   scripts/delete_account.sh a4:cf:12:9b:03:7e   # by badge id
#   scripts/delete_account.sh --emulator          # the desktop badge's fake MAC
#   scripts/delete_account.sh BOBBY --yes         # skip the confirmation
#   scripts/delete_account.sh BOBBY --local       # against wrangler dev
#
# Env overrides:
#   FOXHUNT_SERVER   same as --server (default: prod, where the app points)
set -uo pipefail

cd "$(dirname "$0")/.."

# Prod is the default because that is where registrar.py points: an account
# this script is asked to clean up is, nine times out of ten, one the app
# created on prod without anyone choosing to.
BASE="${FOXHUNT_SERVER:-https://foxhunt.enigmeta.workers.dev}"
# Must match registrar.badge_id's desktop fallback.
EMULATOR_BADGE="a4:cf:12:9b:03:7e"
TARGET=""
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --server) BASE="${2:-}"; shift 2 ;;
        --local) BASE="http://localhost:8787"; shift ;;
        --emulator) TARGET="$EMULATOR_BADGE"; shift ;;
        -y|--yes) ASSUME_YES=1; shift ;;
        -h|--help) sed -n '2,31p' "$0"; exit 0 ;;
        -*) echo "error: unknown option '$1'" >&2; exit 2 ;;
        *)
            [[ -n "$TARGET" ]] && { echo "error: one account at a time" >&2; exit 2; }
            TARGET="$1"; shift ;;
    esac
done

command -v jq >/dev/null || { echo "error: jq is required" >&2; exit 1; }

PLAYERS=$(curl -sf -m 10 -H 'Accept: application/json' "$BASE/debug/players") || {
    echo "error: no server at $BASE" >&2
    exit 1
}

echo "server: $BASE"

# The listing is also the picker: with no argument, show what is there and stop.
list() {
    echo "$PLAYERS" | jq -r '
        if length == 0 then "  (no accounts)"
        else .[] | "  \(.badge_id)  \(.name)  \(.creature_count) beest(en)\(
            if .dt_deleted then "  [GEWIST \(.dt_deleted)]" else "" end)"
        end'
}

if [[ -z "$TARGET" ]]; then
    echo "accounts:"
    list
    echo
    echo "pass a name or badge id to delete one; --help for more"
    exit 0
fi

# Badge id first, then name — a name is what the badge shows you, but two
# players may share one and only the badge id is unique.
MATCHES=$(echo "$PLAYERS" | jq --arg t "$TARGET" \
    '[.[] | select((.badge_id | ascii_downcase) == ($t | ascii_downcase))]')
if [[ "$(echo "$MATCHES" | jq 'length')" == "0" ]]; then
    MATCHES=$(echo "$PLAYERS" | jq --arg t "$TARGET" \
        '[.[] | select((.name | ascii_downcase) == ($t | ascii_downcase))]')
fi

COUNT=$(echo "$MATCHES" | jq 'length')
if [[ "$COUNT" == "0" ]]; then
    echo "error: no account matches '$TARGET'" >&2
    echo "accounts:" >&2
    list >&2
    exit 1
fi
if [[ "$COUNT" != "1" ]]; then
    echo "error: '$TARGET' matches $COUNT accounts — use a badge id" >&2
    echo "$MATCHES" | jq -r '.[] | "  \(.badge_id)  \(.name)"' >&2
    exit 1
fi

BADGE=$(echo "$MATCHES" | jq -r '.[0].badge_id')
NAME=$(echo "$MATCHES" | jq -r '.[0].name')
CREATURES=$(echo "$MATCHES" | jq -r '.[0].creature_count')
HUNTER=$(echo "$MATCHES" | jq -r '.[0].hunter_id // "geen"')
DELETED=$(echo "$MATCHES" | jq -r '.[0].dt_deleted // ""')

echo
echo "  name       $NAME"
echo "  badge_id   $BADGE"
echo "  hunter_id  $HUNTER"
echo "  beesten    $CREATURES"
[[ -n "$DELETED" ]] && echo "  already wiped at $DELETED"
echo

if [[ -n "$DELETED" ]]; then
    echo "nothing to do — this account is already wiped."
    echo "to undo one, clear players.dt_deleted for badge_id = '$BADGE'."
    exit 0
fi

if [[ "$ASSUME_YES" != "1" ]]; then
    # The catch list is the part that does not come back: DELETE only stamps
    # dt_deleted, but the next registration on this badge revives the row and
    # drops every creature with it.
    printf "delete this account from %s? [y/N] " "$BASE"
    read -r answer
    [[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "cancelled."; exit 1; }
fi

OUT=$(curl -s -w '\n%{http_code}' -m 15 -X DELETE "$BASE/api/v1/auth/user" \
      -H 'content-type: application/json' -d "{\"badge_id\":\"$BADGE\"}")
STATUS=${OUT##*$'\n'}
BODY=${OUT%$'\n'*}

if [[ "$STATUS" != "200" ]]; then
    echo "error: server refused (HTTP $STATUS): $BODY" >&2
    exit 1
fi

echo "wiped. $NAME is off the scoreboard and out of restore."
echo "the row is kept with dt_deleted stamped — clear that column to undo,"
echo "but registering again on this badge revives it and drops its beesten."
