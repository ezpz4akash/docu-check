#!/usr/bin/env bash
# start.sh
set -e

# default port Render gives is 10000; allow OVERRIDE_PORT env
PORT="${PORT:-10000}"

# ensure /tmp/docucheck exists for temporary files
mkdir -p /tmp/docucheck
uvicorn backend.app:app --host 0.0.0.0 --port "$PORT" --workers 1
