#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export QDRANT_PATH="${QDRANT_PATH:-qdrant_storage/deploy}"
export RETRIEVAL_MODE="${RETRIEVAL_MODE:-sparse}"
export PORT="${PORT:-7860}"
export SKIP_STARTUP_WARMUP="${SKIP_STARTUP_WARMUP:-1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export TOKENIZERS_PARALLELISM=false
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"

CHUNKS="${QDRANT_PATH}/chunks.jsonl"
if [[ ! -f "${CHUNKS}" ]]; then
  echo "ERROR: missing sparse index at ${CHUNKS}."
  echo "Rebuild the Docker image (index is created at build time)."
  exit 1
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
