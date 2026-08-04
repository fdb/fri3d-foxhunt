#!/usr/bin/env bash
# Bake artwork/ into the app's assets — one sprite atlas plus mirrored PNGs.
# Thin wrapper; the real work (and the format documentation) lives in
# scripts/bake_atlas.py. Same contract as always:
#
#   scripts/bake_sprites.sh            # (re-)bake, prune orphans
#   scripts/bake_sprites.sh --check    # report drift, exit 1 (CI)
set -euo pipefail
exec uv run --quiet "$(dirname "$0")/bake_atlas.py" "$@"
