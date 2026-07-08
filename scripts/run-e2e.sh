#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${SKIP_FRONTEND_BUILD:-0}" != "1" ]]; then
  (cd frontend && npm install && npm run build)
fi

npm install
npx playwright install chromium
npm run test:e2e "$@"
