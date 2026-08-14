#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CLOUDFLARED="${CLOUDFLARED:-$PWD/.cache/cloudflared}"
APP_URL="${APP_URL:-http://127.0.0.1:8000}"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if ! curl -fsS "${APP_URL}/health" >/dev/null 2>&1; then
  source .venv/bin/activate
  uvicorn backend.main:app --host 127.0.0.1 --port 8000 \
    >"/tmp/voice-rag-goa.log" 2>&1 &
  SERVER_PID=$!
  for _ in {1..60}; do
    curl -fsS "${APP_URL}/health" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS "${APP_URL}/health" >/dev/null
fi

if [[ ! -x "${CLOUDFLARED}" ]]; then
  mkdir -p "$(dirname "${CLOUDFLARED}")"
  curl -L --fail --retry 3 \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o "${CLOUDFLARED}"
  chmod +x "${CLOUDFLARED}"
fi

echo "Keep this terminal open; the public URL appears below."
exec "${CLOUDFLARED}" tunnel --url "${APP_URL}" --no-autoupdate
