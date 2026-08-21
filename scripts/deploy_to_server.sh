#!/usr/bin/env bash
# Deploy the cloud server to Cloudflare (https://foxhunt.enigmeta.com).
#
# Typechecks first so a broken worker never ships. Schema changes are NOT
# applied automatically — run `npm run db:init:remote` in server/ for those.
set -euo pipefail
cd "$(dirname "$0")/../server"

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run typecheck
npm run deploy
