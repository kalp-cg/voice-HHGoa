#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate
exec uvicorn backend.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
