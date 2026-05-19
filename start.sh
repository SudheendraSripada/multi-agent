#!/usr/bin/env bash
# Use the project venv (created in build). System python3 has no pip packages.
set -o errexit
cd "$(dirname "$0")"

VENV_PY=".venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "Missing .venv — run build: python3 -m venv .venv && .venv/bin/pip install -r requirements-agency.txt" >&2
  exit 1
fi

exec "$VENV_PY" -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}"
