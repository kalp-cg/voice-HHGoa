#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export QDRANT_PATH="${QDRANT_PATH:-qdrant_storage/deploy}"
export PORT="${PORT:-7860}"

if [[ ! -f "${QDRANT_PATH}/meta.json" ]]; then
  extra=()
  if [[ -n "${INPUT_JSONL:-}" && -f "${INPUT_JSONL}" ]]; then
    extra+=(--input-jsonl "${INPUT_JSONL}")
  fi
  python scripts/build_streaming_index.py \
    --language "${DATASET_LANGUAGE:-hi}" \
    --split "${DATASET_SPLIT:-validation}" \
    --records "${DATASET_RECORDS:-10000}" \
    --max-chunks "${DATASET_CHUNKS:-12000}" \
    --qdrant-path "${QDRANT_PATH}" \
    --recreate \
    "${extra[@]}"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
