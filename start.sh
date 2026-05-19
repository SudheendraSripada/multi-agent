#!/usr/bin/env bash
set -o errexit

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "No Python interpreter found on PATH" >&2
  exit 127
fi

exec "$PY" -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}"
