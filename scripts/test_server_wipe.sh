#!/usr/bin/env bash
# Walk the account-wipe lifecycle against a running server.
#
# The wipe (server/README.md, "Wiping an account") is soft, and every one of its
# properties is a thing some OTHER route must now refuse: restore, PATCH,
# /found, the scoreboard. Those are four separate filters, and a missed one is
# invisible until a wiped player turns up on the public board — so this walks the
# whole life of an account instead of testing the DELETE alone.
#
# It registers a throwaway badge id, so it is safe to run repeatedly. Point it
# at prod only if you mean to leave a wiped test row there.
#
# Usage:
#   npm --prefix server run dev &      # then, in another shell:
#   scripts/test_server_wipe.sh
#   scripts/test_server_wipe.sh --server https://foxhunt.enigmeta.workers.dev
#
# Env overrides:
#   FOXHUNT_SERVER      same as --server (default: the local wrangler dev worker)
#   FOXHUNT_DEBUG_KEY   the server's DEBUG_KEY secret, when /debug is locked
set -uo pipefail

cd "$(dirname "$0")/.."

BASE="${FOXHUNT_SERVER:-http://localhost:8787}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --server) BASE="${2:-}"; shift 2 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

curl -sf -o /dev/null -m 5 "$BASE/" || {
    echo "error: no server at $BASE (start one with: npm --prefix server run dev)" >&2
    exit 1
}

# A fresh badge id per run: the test ends with a REVIVED account on this id, and
# reusing one would start the next run from that state instead of from nothing.
BADGE="aa:bb:cc:$(printf '%02x:%02x:%02x' $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)))"
PASS=0
FAIL=0
STATUS=""
BODY=""

req() { # req METHOD PATH [json-body] -> STATUS, BODY
    local method=$1 path=$2 data=${3:-} out
    if [[ -n "$data" ]]; then
        out=$(curl -s -w '\n%{http_code}' -X "$method" "$BASE$path" \
              -H 'content-type: application/json' -d "$data")
    else
        out=$(curl -s -w '\n%{http_code}' -X "$method" "$BASE$path")
    fi
    STATUS=${out##*$'\n'}
    BODY=${out%$'\n'*}
}

ok()   { echo "ok    $1"; PASS=$((PASS + 1)); }
bad()  { echo "FAIL  $1"; FAIL=$((FAIL + 1)); }

check() { # check LABEL WANT-STATUS [BODY-SUBSTRING]
    local label=$1 want=$2 needle=${3:-}
    if [[ "$STATUS" != "$want" ]]; then
        bad "$label — want HTTP $want, got $STATUS: $BODY"
    elif [[ -n "$needle" && "$BODY" != *"$needle"* ]]; then
        bad "$label — body has no '$needle': $BODY"
    else
        ok "$label ($STATUS)"
    fi
}

json_num() { sed -n "s/.*\"$1\":\([0-9]*\).*/\1/p" <<<"$BODY"; }

echo "server: $BASE"
echo "badge:  $BADGE"
echo
echo "--- a normal account ---"

req POST /api/v1/auth/register \
    "{\"badge_id\":\"$BADGE\",\"name\":\"Testjager\",\"profile_pic\":\"H01A003C1\"}"
check "register a fresh badge" 201 '"starter"'
PLAYER_ID=$(json_num id)
STARTER=$(json_num starter)
echo "      player #$PLAYER_ID, startbeest $STARTER"

req POST /api/v1/auth/register "{\"badge_id\":\"$BADGE\",\"name\":\"Dubbel\"}"
check "registering twice is the 409 fork, not a second row" 409 "already registered"

req GET "/api/v1/auth/user?badge_id=$BADGE"
check "restore finds it" 200 "Testjager"

# fox 13 is the one creature an unbridged caller may claim, so the account has a
# catch list the wipe has to take with it.
req POST /api/v1/player/found "{\"badge_id\":\"$BADGE\",\"fox_id\":13}"
check "a find lands" 200 '"ok":true'

if curl -s "$BASE/scores" | grep -q Testjager; then
    ok "on the public scoreboard"
else
    bad "not on the public scoreboard before the wipe"
fi

echo
echo "--- wipe ---"

req DELETE /api/v1/auth/user "{\"badge_id\":\"$BADGE\"}"
check "delete" 200 '"ok":true'

req DELETE /api/v1/auth/user "{\"badge_id\":\"$BADGE\"}"
check "deleting again is idempotent" 200 '"already":true'

req GET "/api/v1/auth/user?badge_id=$BADGE"
check "restore 404s — the badge looks new again" 404

req PATCH /api/v1/auth/user "{\"badge_id\":\"$BADGE\",\"name\":\"Kaper\"}"
check "PATCH cannot touch a wiped account" 404

req POST /api/v1/player/found "{\"badge_id\":\"$BADGE\",\"fox_id\":13}"
check "a find cannot resurrect it" 404

req POST /api/v1/auth/starter "{\"badge_id\":\"$BADGE\"}"
check "the startbeest catch-up route skips it" 404

if curl -s "$BASE/scores" | grep -q Testjager; then
    bad "still on the public scoreboard after the wipe"
else
    ok "off the public scoreboard"
fi

if curl -s -H 'Accept: application/json' \
    ${FOXHUNT_DEBUG_KEY:+-H "Authorization: Bearer $FOXHUNT_DEBUG_KEY"} \
    "$BASE/debug/players" | grep -q "\"id\":$PLAYER_ID,"; then
    ok "still on /debug/players, so an organiser can undo it"
else
    bad "an organiser can no longer see the wiped row"
fi

echo
echo "--- registering again on the same badge ---"

req POST /api/v1/auth/register \
    "{\"badge_id\":\"$BADGE\",\"name\":\"Nieuwe\",\"profile_pic\":\"H02A014C3\"}"
check "revives instead of 409ing" 201 "Nieuwe"
[[ "$(json_num id)" == "$PLAYER_ID" ]] \
    && ok "same row revived (#$PLAYER_ID), no duplicate badge_id" \
    || bad "revive made a new row $(json_num id), want #$PLAYER_ID"

req GET "/api/v1/auth/user?badge_id=$BADGE"
check "restore works again" 200 "Nieuwe"
creatures=$(sed -n 's/.*"creatures":\[\([^]]*\)\].*/\1/p' <<<"$BODY")
[[ "$creatures" == "$STARTER" ]] \
    && ok "roster is the startbeest alone — the old catches are gone" \
    || bad "roster after revive is [$creatures], want [$STARTER]"
[[ "$BODY" == *'"hunter_id":null'* ]] \
    && ok "hunter_id released for the next player" \
    || bad "hunter_id survived the wipe: $BODY"

echo
echo "--- rejections ---"

req DELETE /api/v1/auth/user '{"badge_id":"zz:zz"}'
check "invalid badge_id" 400 "invalid badge_id"

req DELETE /api/v1/auth/user '{"badge_id":"00:00:00:00:00:99"}'
check "unknown badge_id" 404 "unknown badge_id"

req DELETE /api/v1/auth/user 'not json'
check "unparseable body" 400 "invalid JSON body"

echo
echo "$PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
