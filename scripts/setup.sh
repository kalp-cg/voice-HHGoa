#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt
echo "Optional: ollama pull qwen2.5:1.5b"
echo "Index: python scripts/rebuild_index.py --recreate"
echo "Server: ./scripts/start.sh"
