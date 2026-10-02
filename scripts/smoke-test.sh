#!/usr/bin/env sh
# Author: DrPlaga
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ -x .venv/bin/ruff ]; then
  .venv/bin/ruff check .
else
  echo "WARNING: ruff not found at .venv/bin/ruff; lint skipped"
fi

python3 -m pytest
scripts/validate-compose.py
docker compose config >/dev/null
docker compose build browser

echo "PASS: smoke test"
