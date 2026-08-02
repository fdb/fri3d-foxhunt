#!/usr/bin/env bash
# Start the cloud server locally (wrangler dev + local D1).
#
# First run: creates .dev.vars from the example and initialises the local
# D1 database, so the server works out of the box.
set -euo pipefail
cd "$(dirname "$0")/../server"

if [[ ! -f .dev.vars ]]; then
  cp .dev.vars.example .dev.vars
  echo "created .dev.vars from example"
fi

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run db:init:local
npm run dev
