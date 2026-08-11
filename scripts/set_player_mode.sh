#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Flip a USB-connected badge between the two play tracks, from a laptop.
#
# The badge can already go one way by itself (instellingen -> WORD JAGER), and
# only with the physical kit attached. This script does both directions and
# skips the antenna probe on request, so the jager UI is testable on a badge
# whose Wio-SX1262 is not soldered yet.
#
# There is no "mode" flag anywhere. Every screen derives the track from one
# field — `bool(store.profile()["hunter_id"])` — so this script only ever adds
# or removes that field. Home lays itself out differently, uitleg swaps its
# three lines, and store.visitor_pending stops scheduling new fallback visits.
#
#   -> jager        POST /api/v1/auth/hunter mints (or repeats) the id server
#                   side, then the label lands in the badge's profile. The
#                   server is the allocator; this script never invents an id.
#   -> verzamelaar  LOCAL ONLY. The server keeps the hunter_id, because no
#                   route can take one back: PATCH /auth/user refuses the field
#                   outright (freeing an id would let the next caller claim a
#                   jager's finds). So a downgraded badge still shows as
#                   JGR-xxxx on the public scoreboard, and a bridge-attested
#                   find still credits it. That split is the open design
#                   question the badge UI has to answer; here it is printed,
#                   not hidden.
#
# Going jager -> verzamelaar -> jager is lossless: /auth/hunter is idempotent
# and hands back the SAME id, so the round trip cannot reroll or strand it.
#
# Nothing here touches creatures, bond, food or the maatje. Upgrading is
# purely additive by design (GAME_DESIGN.md, "Onboarding: the antenna
# question"), and so is this.
#
# Usage:
#   scripts/set_player_mode.sh                 # report, change nothing
#   scripts/set_player_mode.sh jager
#   scripts/set_player_mode.sh verzamelaar
#   scripts/set_player_mode.sh jager --force   # no antenna kit attached
#   scripts/set_player_mode.sh verzamelaar -y  # skip the confirmation
#   scripts/set_player_mode.sh jager --start   # relaunch the app afterwards
#
# Env overrides:
#   BADGE_PORT       same as --port
#   FOXHUNT_SERVER   same as --server (default: prod, where registrar points)

APP_ID="com.enigmeta.foxhunt"
SERVER="${FOXHUNT_SERVER:-https://foxhunt.enigmeta.workers.dev}"
PORT="${BADGE_PORT:-}"
MODE=""
FORCE=0
ASSUME_YES=0
START=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)     PORT="${2:-}"; shift 2 ;;
        --server)   SERVER="${2:-}"; shift 2 ;;
        --local)    SERVER="http://localhost:8787"; shift ;;
        --force)    FORCE=1; shift ;;
        --start)    START=1; shift ;;
        -y|--yes)   ASSUME_YES=1; shift ;;
        -h|--help)  sed -n '6,46p' "$0"; exit 0 ;;
        jager|hunter)              MODE="jager"; shift ;;
        verzamelaar|gatherer|collector) MODE="verzamelaar"; shift ;;
        *) echo "error: unknown argument '$1' (expected jager or verzamelaar)" >&2; exit 2 ;;
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

# Both server replies are read for one number. Tolerate whitespace after the
# colon: c.json() emits none today, but a parse that breaks on a pretty-printed
# body would fail as "no hunter_id in server reply" while the id sits in it.
json_int() { printf '%s' "$1" | grep -oE "\"$2\"[[:space:]]*:[[:space:]]*[0-9]+" \
             | head -1 | grep -oE '[0-9]+$'; }

# ── 1. Ask the badge who it is and which track it is on ──────────────
# The app's own modules answer: store reads the same SharedPreferences the
# game writes, and registrar.has_lora runs the same receive-only SPI probe
# WORD JAGER runs. No second opinion about either fact.
# The OS keeps running across raw-REPL execs; the sentinel line is the
# verdict, not $? (the REPL folds exceptions into output).
echo "Reading badge state on $PORT..."
state="$("${MP[@]}" exec "
import sys, machine
sys.path.insert(0, '/apps/$APP_ID/assets')
import store, registrar
badge = ':'.join('%02X' % b for b in machine.unique_id())
p = store.profile() or {}
print('STATE', badge, p.get('hunter_id') or '-', p.get('name') or '-',
      'synced' if p.get('synced') else 'unsynced',
      'lora' if registrar.has_lora() else 'nolora',
      len(store.caught_ids()))
" 2>&1)" || { echo "error: badge did not answer; device said:" >&2
              echo "$state" >&2; exit 1; }

case "$state" in
    *"STATE "*) ;;
    *) echo "error: badge did not report its state; device said:" >&2
       echo "$state" >&2; exit 1 ;;
esac
# The serial REPL ends every line with CR, and a non-whitespace IFS char
# delimits without being trimmed — so the LAST field arrives as "3\r" and
# every numeric comparison below silently fails. Drop the CRs before parsing.
state="${state//$'\r'/}"
read -r badge hunter name synced lora caught <<< "${state##*STATE }"

if [[ "$name" == "-" ]]; then
    echo "error: this badge has no profile — nobody to change the mode of." >&2
    echo "       Register on the badge first." >&2
    exit 1
fi

if [[ "$hunter" == "-" ]]; then
    current="verzamelaar"
    modus="verzamelaar"
else
    current="jager"
    modus="jager ($hunter)"
fi
[[ "$lora" == "lora" ]] && antenne="gevonden" || antenne="niet gevonden"

echo "  badge      $badge"
echo "  naam       $name"
echo "  modus      $modus"
echo "  antenne    $antenne"
echo "  beesten    $caught"
if [[ "$synced" == "unsynced" ]]; then
    echo "  cloud      NIET bewaard — dit account bestaat alleen op de badge"
fi

# ── 2. What the server thinks ────────────────────────────────────────
# The two halves can disagree, and that disagreement is the whole point of
# printing it: a local downgrade leaves the server's id in place.
srv="$(curl -sS -m 10 -w $'\n%{http_code}' \
       "$SERVER/api/v1/auth/user?badge_id=$badge" 2>/dev/null || true)"
srv_code="${srv##*$'\n'}"
srv_body="${srv%$'\n'*}"
srv_hunter=""
case "$srv_code" in
    200) srv_hunter="$(json_int "$srv_body" hunter_id)"
         if [[ -n "$srv_hunter" ]]; then
             printf -v srv_label 'JGR-%04d' "$srv_hunter"
             echo "  server     $srv_label"
         else
             echo "  server     verzamelaar (geen hunter_id)"
         fi ;;
    404) echo "  server     kent deze badge niet" ;;
    *)   echo "  server     geen antwoord (HTTP ${srv_code:-?}) — $SERVER" ;;
esac

if [[ -z "$MODE" ]]; then
    echo
    echo "pass 'jager' or 'verzamelaar' to change it; --help for more"
    exit 0
fi

if [[ "$MODE" == "$current" ]]; then
    echo
    echo "nothing to do — this badge is already a $current."
    exit 0
fi

# ── 3. Confirm ───────────────────────────────────────────────────────
echo
if [[ "$MODE" == "jager" ]]; then
    if [[ "$lora" != "lora" ]]; then
        if [[ "$FORCE" != "1" ]]; then
            echo "error: no LoRa radio answered the SPI probe." >&2
            echo "       A jager without an antenna sees the hunt UI and can never" >&2
            echo "       find a fox. Pass --force if that is what you are testing." >&2
            exit 1
        fi
        echo "warning: no antenna found — minting anyway (--force)."
    fi
    echo "This mints a permanent hunter_id on $SERVER."
    echo "Creatures, bond, food and the maatje are untouched."
else
    echo "This removes the hunter_id from THE BADGE ONLY."
    if [[ -n "$srv_hunter" ]]; then
        echo "  * $srv_label stays on the server: no route can take one back,"
        echo "    so the public scoreboard keeps showing this player as a jager"
        echo "    and a bridge-attested find still credits them."
        echo "  * Going back to jager returns the SAME id (the mint is idempotent)."
    fi
    echo "  * Creatures, bond, food and the maatje are untouched."
    echo "  * Home swaps to the verzamelaar layout and fallback visitors can"
    echo "    schedule again."
fi

if [[ "$ASSUME_YES" != "1" ]]; then
    printf "make %s a %s? [y/N] " "$name" "$MODE"
    read -r answer
    [[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "cancelled."; exit 1; }
fi

# ── 4. Mint, when going up ───────────────────────────────────────────
# The server is the allocator (CLAUDE.md, hunter_id): the badge asks and the
# id comes back. Never invent one here — a locally chosen id would collide
# with a real jager's and redirect their finds.
label=""
if [[ "$MODE" == "jager" ]]; then
    echo "Requesting hunter_id from $SERVER..."
    resp="$(curl -sS -m 15 -w $'\n%{http_code}' -X POST "$SERVER/api/v1/auth/hunter" \
            -H 'Content-Type: application/json' \
            -d "{\"badge_id\": \"$badge\"}")"
    code="${resp##*$'\n'}"
    body="${resp%$'\n'*}"
    case "$code" in
        200) ;;
        404) echo "error: the server does not know this badge ($body)." >&2
             echo "       Register (or resync) on the badge first — /auth/hunter" >&2
             echo "       looks the account up and cannot mint for one that is" >&2
             echo "       missing." >&2
             exit 1 ;;
        *)   echo "error: server said HTTP $code: $body" >&2; exit 1 ;;
    esac
    hid="$(json_int "$body" hunter_id)"
    [[ -n "$hid" ]] || { echo "error: no hunter_id in server reply: $body" >&2; exit 1; }
    # The badge stores the LABEL, the server the integer — registrar._hunter_label
    # is the seam, and every screen prints what the profile holds verbatim.
    printf -v label 'JGR-%04d' "$hid"
    if [[ "$body" == *'"minted"'*true* ]]; then
        echo "  minted $label"
    else
        echo "  $label (already allocated to this badge)"
    fi
fi

# ── 5. Write the badge's profile ─────────────────────────────────────
# Back to the launcher first. A live activity holds its own SharedPreferences
# snapshot, and its next commit would write the whole file back — hunter_id
# included — silently undoing this (CLAUDE.md, "One SharedPreferences
# instance, one editor, per write path").
"${MP[@]}" exec "
from mpos import AppManager
AppManager.restart_launcher()" >/dev/null 2>&1 || true

# put_dict writes the value as given, so None is a real stored None and
# profile().get('hunter_id') is falsy — which is exactly what every screen
# tests. There is no key to remove (Editor has no remove()).
py_value="None"
if [[ -n "$label" ]]; then
    py_value="'$label'"
fi
out="$("${MP[@]}" exec "
import sys
sys.path.insert(0, '/apps/$APP_ID/assets')
import store
p = store.update_profile(hunter_id=$py_value)
print('MODE', p.get('hunter_id') or 'verzamelaar')
" 2>&1)"

case "$out" in
    *"MODE "*)
        # Echo what the badge read BACK out of its own profile, not what we
        # asked it to write: the round trip is the only proof the commit stuck.
        got="${out##*MODE }"
        got="${got%%[$'\r\n']*}"
        if [[ "$got" == "verzamelaar" ]]; then
            echo "Badge is now a verzamelaar."
        else
            echo "Badge is now a jager ($got)."
        fi ;;
    *)  echo "error: the badge write failed:" >&2
        echo "$out" >&2
        if [[ -n "$label" ]]; then
            echo "       $label is allocated on the server; re-running is safe" >&2
            echo "       (the mint repeats the same id)." >&2
        fi
        exit 1 ;;
esac

if [[ "$MODE" == "verzamelaar" && -n "$srv_hunter" ]]; then
    echo "Note: $srv_label is still on the server. /scores and the LoRa bridge"
    echo "      still see this player as a jager."
fi

if [[ "$START" == "1" ]]; then
    "${MP[@]}" exec "
from mpos import AppManager
AppManager.start_app('$APP_ID')" >/dev/null 2>&1 || true
    echo "Started $APP_ID."
fi
