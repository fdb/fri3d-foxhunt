#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

repo_root="$(cd .. && pwd)"
backup_dir="$repo_root/backups"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="$backup_dir/foxhunt-prod-$timestamp.sql"
temporary="$backup_dir/.foxhunt-prod-$timestamp.$$.sql"

mkdir -p "$backup_dir"
if [[ -e "$output" ]]; then
    echo "backup already exists: $output" >&2
    exit 1
fi

cleanup() {
    rm -f "$temporary"
}
trap cleanup EXIT

(
    cd "$repo_root/server"
    npx wrangler d1 export foxhunt \
        --remote \
        --skip-confirmation \
        --output "$temporary"
)

if [[ ! -s "$temporary" ]]; then
    echo "D1 export produced an empty backup" >&2
    exit 1
fi

chmod 600 "$temporary"
mv "$temporary" "$output"
trap - EXIT

echo "$output"
