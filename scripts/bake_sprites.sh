#!/usr/bin/env bash
# Bake the artwork into the image files the app loads.
#
# artwork/**/*.png  →  be.fri3d.foxhunt/assets/**/*.png   (same structure)
#
# artwork/ is the source of truth (PNGs plus their .aseprite sources); the
# mirror under assets/ is the deployed artifact — an exact PNG-only copy, no
# symlink, so a plain copy of the app dir is badge-ready. Both are committed,
# because the badge has no build step: whatever sits in assets/ is what runs.
#
# The tree structure is preserved, so artwork/animals/vos.png lands at
# assets/animals/vos.png and artwork/title-screen/title-screen.png at
# assets/title-screen/title-screen.png. Every PNG under assets/ belongs to this
# script (the hand-maintained things there are .py and fonts/*.bin), so a PNG
# with no artwork behind it is pruned.
#
# Usage:
#   scripts/bake_sprites.sh            # (re-)mirror every PNG, prune orphans
#   scripts/bake_sprites.sh --check    # report stale/missing/orphan, change
#                                      # nothing (exit 1 if out of date — CI)
set -euo pipefail

cd "$(dirname "$0")/.."

mode="write"
case "${1:-}" in
    "")        mode="write" ;;
    --check)   mode="check" ;;
    *)         echo "usage: $0 [--check]" >&2; exit 2 ;;
esac

src_dir="artwork"
out_dir="be.fri3d.foxhunt/assets"

if [[ -L "$out_dir" ]]; then
    echo "bake_sprites: $out_dir is a symlink — remove it first" >&2
    exit 1
fi

fail=0

# Source → mirror: copy every PNG whose mirror is missing or stale.
while IFS= read -r -d '' png; do
    rel="${png#"$src_dir"/}"
    out="$out_dir/$rel"
    if [[ -f "$out" ]] && cmp -s "$png" "$out"; then
        continue
    fi
    if [[ "$mode" == "check" ]]; then
        [[ -f "$out" ]] && echo "stale: $out (does not match $png)" \
                        || echo "missing: $out"
        fail=1
    else
        echo "baking: $png -> $out"
        mkdir -p "$(dirname "$out")"
        cp "$png" "$out"
    fi
done < <(find "$src_dir" -name '*.png' -print0)

# Mirror → source: an image with no artwork behind it is unmaintainable — prune.
if [[ -d "$out_dir" ]]; then
    while IFS= read -r -d '' out; do
        rel="${out#"$out_dir"/}"
        if [[ ! -f "$src_dir/$rel" ]]; then
            if [[ "$mode" == "check" ]]; then
                echo "orphan: $out (no $src_dir/$rel)"
                fail=1
            else
                echo "pruning: $out"
                rm "$out"
            fi
        fi
    done < <(find "$out_dir" -name '*.png' -print0)
    [[ "$mode" == "write" ]] && find "$out_dir" -type d -empty -delete
fi

if [[ "$mode" == "check" && "$fail" -ne 0 ]]; then
    echo "artwork out of date — run scripts/bake_sprites.sh" >&2
    exit 1
fi
