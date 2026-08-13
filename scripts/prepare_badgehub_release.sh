#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
cd ..

# Run the complete local release gate, build the bytecode-only package twice,
# verify it is reproducible, and collect Git evidence for release notes.
#
# Usage: scripts/prepare_badgehub_release.sh [--base <git-ref>] [--allow-dirty]
# --allow-dirty exists only for developing this workflow. Never use it for an
# artifact that may be uploaded: its commit and checksum would not identify its
# source tree faithfully.

APP_DIR="com.enigmeta.foxhunt"
MANIFEST="$APP_DIR/MANIFEST.JSON"
DIST="dist"
base_override=""
allow_dirty=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base)
            [[ $# -ge 2 ]] || { echo "error: --base requires a git ref" >&2; exit 2; }
            base_override="$2"
            shift 2
            ;;
        --allow-dirty)
            allow_dirty=1
            shift
            ;;
        *)
            echo "usage: $0 [--base <git-ref>] [--allow-dirty]" >&2
            exit 2
            ;;
    esac
done

command -v git >/dev/null || { echo "error: git is required" >&2; exit 1; }
command -v npm >/dev/null || { echo "error: npm is required" >&2; exit 1; }
command -v unzip >/dev/null || { echo "error: unzip is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "error: uv is required (https://docs.astral.sh/uv/)" >&2; exit 1; }
[[ -f "$MANIFEST" ]] || { echo "error: missing $MANIFEST" >&2; exit 1; }

version="$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['version'])")"
app_id="$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['fullname'])")"
entrypoint="$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['activities'][0]['entrypoint'])")"
classname="$(uv run --no-project python -c "import json; print(json.load(open('$MANIFEST'))['activities'][0]['classname'])")"

[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]] || { echo "error: manifest version is not semantic: $version" >&2; exit 1; }
[[ "$app_id" == "$APP_DIR" ]] || { echo "error: manifest fullname '$app_id' does not match '$APP_DIR'" >&2; exit 1; }
[[ "$entrypoint" == *.py ]] || { echo "error: manifest entrypoint must name its source .py file: $entrypoint" >&2; exit 1; }
[[ -f "$APP_DIR/$entrypoint" ]] || { echo "error: manifest entrypoint does not exist: $APP_DIR/$entrypoint" >&2; exit 1; }
rg -q "class[[:space:]]+$classname\b" "$APP_DIR/$entrypoint" || { echo "error: $entrypoint does not define $classname" >&2; exit 1; }

dirty="$(git status --porcelain=v1)"
if [[ -n "$dirty" && "$allow_dirty" -ne 1 ]]; then
    echo "error: release candidates require a clean worktree:" >&2
    printf '%s\n' "$dirty" >&2
    exit 1
fi
if [[ -n "$dirty" ]]; then
    echo "warning: building from a dirty worktree (--allow-dirty)" >&2
fi

echo "Preparing BadgeHub candidate $app_id $version"
echo "  entrypoint: $entrypoint -> $classname"
echo "  commit:    $(git rev-parse --short HEAD)"

run_check() {
    local label="$1"
    shift
    echo
    echo "==> $label"
    "$@"
}

check_server_format() (
    cd server
    # scripts/format.sh owns JSON repository-wide through json.tool. Prettier
    # disagrees with it on tsconfig.json, so keep this check to the server
    # languages that have no other formatter.
    npm exec -- prettier --check "src/**/*.{ts,tsx}" "static/**/*.css"
)

run_check "Python and JSON formatting" scripts/format.sh --check
run_check "Python tests" uvx pytest tests/ -q
run_check "Sprite atlas drift" scripts/bake_sprites.sh --check
run_check "Font drift" scripts/bake_fonts.sh --check
run_check "Server companion-art drift" scripts/bake_server_art.sh --check
run_check "Server icon drift" scripts/bake_server_icons.sh --check
run_check "Server typecheck" npm --prefix server run typecheck
run_check "Server formatting" check_server_format

mkdir -p "$DIST"
first_build="$(mktemp)"
trap 'rm -f "$first_build"' EXIT

run_check "First bytecode-only MPK build" scripts/build_mpk.sh
mpk="$DIST/${app_id}_${version}.mpk"
[[ -f "$mpk" ]] || { echo "error: expected build output missing: $mpk" >&2; exit 1; }
cp "$mpk" "$first_build"
first_sha="$(shasum -a 256 "$first_build" | awk '{print $1}')"

run_check "Reproducibility build" scripts/build_mpk.sh
second_sha="$(shasum -a 256 "$mpk" | awk '{print $1}')"
[[ "$first_sha" == "$second_sha" ]] || { echo "error: repeated builds differ: $first_sha != $second_sha" >&2; exit 1; }

archive_entries="$(unzip -Z1 "$mpk")"
[[ -n "$archive_entries" ]] || { echo "error: package is empty" >&2; exit 1; }
if printf '%s\n' "$archive_entries" | rg -q '(^/|(^|/)\.\.(/|$))'; then
    echo "error: package contains an unsafe path" >&2
    exit 1
fi
outside_entry="$(printf '%s\n' "$archive_entries" | awk -v prefix="$app_id/" 'index($0, prefix) != 1 { print; exit }')"
if [[ -n "$outside_entry" ]]; then
    echo "error: package contains a path outside top-level $app_id/" >&2
    echo "       $outside_entry" >&2
    exit 1
fi
if printf '%s\n' "$archive_entries" | rg -q '\.py$'; then
    echo "error: package contains Python source; BadgeHub builds must be bytecode-only" >&2
    printf '%s\n' "$archive_entries" | rg '\.py$' >&2
    exit 1
fi
if printf '%s\n' "$archive_entries" | rg -q '(^|/)(__pycache__|\.DS_Store)(/|$)'; then
    echo "error: package contains development artifacts" >&2
    exit 1
fi
cmp -s "$MANIFEST" <(unzip -p "$mpk" "$app_id/MANIFEST.JSON") || { echo "error: packaged manifest differs from source" >&2; exit 1; }

while IFS= read -r source; do
    relative="${source#"$APP_DIR/"}"
    compiled="$app_id/${relative%.py}.mpy"
    printf '%s\n' "$archive_entries" | rg -Fxq "$compiled" || { echo "error: missing compiled module $compiled" >&2; exit 1; }
done < <(find "$APP_DIR" -type f -name '*.py' | sort)

compiled_entry="$app_id/${entrypoint%.py}.mpy"
printf '%s\n' "$archive_entries" | rg -Fxq "$compiled_entry" || { echo "error: compiled entrypoint missing: $compiled_entry" >&2; exit 1; }

if [[ -n "$base_override" ]]; then
    git rev-parse --verify --quiet "${base_override}^{commit}" >/dev/null || { echo "error: unknown base ref: $base_override" >&2; exit 1; }
    base="$base_override"
    base_reason="explicit --base"
else
    current_tag="v$version"
    if git rev-parse --verify --quiet "refs/tags/$current_tag^{commit}" >/dev/null && git merge-base --is-ancestor "$current_tag" HEAD; then
        base="$(git describe --tags --abbrev=0 --match 'v[0-9]*' "$current_tag^" 2>/dev/null || true)"
    else
        base="$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || true)"
    fi
    if [[ -n "$base" ]]; then
        base_reason="latest prior reachable semantic-version tag"
    else
        base="$(git rev-list --max-parents=0 HEAD | tail -1)"
        base_reason="initial release (no reachable v* tag)"
    fi
fi

if [[ "$base_reason" == "initial release (no reachable v* tag)" ]]; then
    log_range="HEAD"
    diff_range="$base..HEAD"
else
    log_range="$base..HEAD"
    diff_range="$base..HEAD"
fi

context="$DIST/badgehub-release-${version}-context.md"
commit_count="$(git rev-list --count --no-merges "$log_range")"
byte_size="$(wc -c <"$mpk" | tr -d ' ')"
{
    echo "# BadgeHub release context"
    echo
    echo "- App: $app_id"
    echo "- Version: $version"
    echo "- Commit: $(git rev-parse HEAD)"
    echo "- Worktree: $([[ -z "$dirty" ]] && echo clean || echo dirty-development-build)"
    echo "- Baseline: $base ($base_reason)"
    echo "- Non-merge commits considered: $commit_count"
    echo "- Artifact: $mpk"
    echo "- Bytes: $byte_size"
    echo "- SHA-256: $second_sha"
    echo "- Entrypoint: $entrypoint -> $classname"
    echo
    echo "## Changed files"
    echo
    echo '```text'
    git diff --name-status "$diff_range"
    echo '```'
    echo
    echo "## Diff summary"
    echo
    echo '```text'
    git diff --stat "$diff_range"
    echo '```'
    echo
    echo "## Non-merge commits (oldest first)"
    echo
    echo '```text'
    git log --reverse --no-merges --date=short --format='%h  %ad  %s' "$log_range"
    echo '```'
} >"$context"

echo
echo "BadgeHub candidate is mechanically ready"
echo "  artifact: $mpk"
echo "  bytes:    $byte_size"
echo "  sha256:   $second_sha"
echo "  context:  $context"
echo "  baseline: $base ($base_reason)"
echo
echo "Manual code review and an exact-artifact smoke test on the Fri3d badge remain required."
