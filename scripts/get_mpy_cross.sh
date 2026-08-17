#!/bin/bash
set -euo pipefail

# Produce an mpy-cross that matches the badge's firmware, on a machine that has
# no MicroPythonOS checkout — a build server, a fresh laptop, CI.
#
# Prints the path to the compiler on stdout; everything else goes to stderr, so
# callers can do  MPY_CROSS="$(scripts/get_mpy_cross.sh)".
#
# WHY this exists at all: a .mpy is only loadable by a firmware whose MPY_VERSION
# matches, which is why build_mpk.sh and deploy_to_badge.sh have always used the
# mpy-cross sitting inside the developer's own MicroPythonOS checkout. That rule
# is right and stays — but it makes "you must first build the firmware" a
# prerequisite for producing a store package, and no build server is going to do
# that (the firmware needs esp-idf; mpy-cross needs a C compiler and 30 seconds).
# So instead of a checkout, this script reconstructs the same compiler from the
# pins MicroPythonOS itself publishes, walking the submodule chain:
#
#     MicroPythonOS <ref>  ->  lvgl_micropython  ->  lib/micropython
#
# Each step reads the sha out of the parent's tree rather than assuming a
# version, so what comes out is the compiler the firmware was built with and not
# "some MicroPython 1.25".
#
# Measured when this was written: MicroPythonOS 0.12.0, 0.15.0 and 0.17.2 all
# pin the SAME micropython (78ff170), i.e. every OS version the badge is
# plausibly running wants identical bytecode, and the emulator (0.17.3) reports
# that same bytecode version, `_mpy=774`. EXPECTED_MICROPYTHON records it. When a
# future MicroPythonOS bumps it, this script FAILS instead of quietly emitting
# .mpy that the badge would refuse at import time — the one failure mode worth
# being loud about, because it surfaces as "the app just doesn't start" on
# hardware and nowhere earlier.
#
# The build is cached per micropython sha, so the second run costs nothing and
# needs no network at all.
#
# Usage:  scripts/get_mpy_cross.sh
# Env:
#   MPY_CROSS_CACHE      where to keep sources + built compilers
#                        (default: ~/.cache/foxhunt/mpy-cross)
#   MPOS_REF             MicroPythonOS tag/branch/sha to take pins from
#                        (default: $MPOS_REF_DEFAULT below)
#   MICROPYTHON_COMMIT   skip pin resolution and build exactly this commit.
#                        Also the escape hatch for the EXPECTED mismatch above:
#                        set it deliberately once you have checked the new pin.
#   FORCE=1              rebuild even when the cache already has the compiler

MPOS_REF_DEFAULT="0.17.2"
EXPECTED_MICROPYTHON="78ff170de9e32c79db6e64d3e33d2bd60002bdcd"

CACHE="${MPY_CROSS_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/foxhunt/mpy-cross}"
MPOS_REF="${MPOS_REF:-$MPOS_REF_DEFAULT}"
SRC="$CACHE/src"

log() { echo "$@" >&2; }

# Fast path: the compiler we are going to be asked for is already built. Checked
# against the EXPECTED sha (not a resolved one) precisely so a cache hit needs no
# network — a CI run with a warm cache does zero git traffic.
cached="$CACHE/${MICROPYTHON_COMMIT:-$EXPECTED_MICROPYTHON}/mpy-cross"
if [[ -x "$cached" && -z "${FORCE:-}" ]]; then
    echo "$cached"
    exit 0
fi

command -v git >/dev/null || { log "error: git is required"; exit 1; }
command -v make >/dev/null || { log "error: make is required"; exit 1; }
command -v cc >/dev/null || command -v gcc >/dev/null || { log "error: a C compiler is required"; exit 1; }

# Shallow-fetch one commit/tag into a reusable dir. `--depth 1` on a bare sha
# needs the server to allow reachable-sha1-in-want; GitHub does, which is what
# keeps this to a few MB instead of cloning micropython's full history.
fetch_at() { # $1=url  $2=dir  $3=ref
    mkdir -p "$2"
    git -C "$2" rev-parse --git-dir >/dev/null 2>&1 || git -C "$2" init -q
    git -C "$2" remote get-url origin >/dev/null 2>&1 || git -C "$2" remote add origin "$1"
    git -C "$2" fetch -q --depth 1 origin "$3"
    git -C "$2" checkout -q FETCH_HEAD
}
pin_of() { git -C "$1" ls-tree HEAD "$2" | awk '{print $3}'; } # submodule sha

if [[ -n "${MICROPYTHON_COMMIT:-}" ]]; then
    mp="$MICROPYTHON_COMMIT"
    log "using pinned micropython $mp (MICROPYTHON_COMMIT set, pin resolution skipped)"
else
    log "resolving the badge's bytecode target from MicroPythonOS $MPOS_REF..."
    fetch_at https://github.com/MicroPythonOS/MicroPythonOS.git "$SRC/mpos" "$MPOS_REF"
    lvgl="$(pin_of "$SRC/mpos" lvgl_micropython)"
    fetch_at https://github.com/MicroPythonOS/lvgl_micropython "$SRC/lvgl_micropython" "$lvgl"
    mp="$(pin_of "$SRC/lvgl_micropython" lib/micropython)"
    log "  MicroPythonOS $MPOS_REF -> lvgl_micropython ${lvgl:0:8} -> micropython ${mp:0:8}"

    if [[ "$mp" != "$EXPECTED_MICROPYTHON" ]]; then
        log ""
        log "error: MicroPythonOS $MPOS_REF pins micropython $mp,"
        log "       but this script expects $EXPECTED_MICROPYTHON."
        log ""
        log "       The bytecode target moved. Check whether the new commit still emits the"
        log "       same .mpy version (py/persistentcode.h: MPY_VERSION / MPY_SUB_VERSION) and"
        log "       whether the badge in the field runs a firmware built from it, then update"
        log "       EXPECTED_MICROPYTHON here. To build it once without editing: "
        log "       MICROPYTHON_COMMIT=$mp $0"
        exit 1
    fi
fi

out="$CACHE/$mp/mpy-cross"
if [[ -x "$out" && -z "${FORCE:-}" ]]; then
    echo "$out"
    exit 0
fi

log "building mpy-cross from micropython ${mp:0:8} (once; cached in $CACHE)..."
fetch_at https://github.com/micropython/micropython "$SRC/micropython" "$mp"
make -C "$SRC/micropython/mpy-cross" -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)" >&2

mkdir -p "$(dirname "$out")"
cp "$SRC/micropython/mpy-cross/build/mpy-cross" "$out"
log "  $("$out" --version 2>&1 | head -1)"

echo "$out"
