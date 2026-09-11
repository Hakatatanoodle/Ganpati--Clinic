#!/usr/bin/env bash
# One-shot launcher for the Multi-LLM Arena.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
if [ ! -d frontend/dist ]; then
  (cd frontend && npm run build)
fi

exec .venv/bin/uvicorn --app-dir backend main:app --host 0.0.0.0 --port "${PORT:-8000}"
