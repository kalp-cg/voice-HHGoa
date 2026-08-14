#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate
python evaluation/build_queries.py
python evaluation/benchmark.py --mode fast
