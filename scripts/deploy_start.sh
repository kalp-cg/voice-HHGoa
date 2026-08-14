#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export QDRANT_PATH="${QDRANT_PATH:-qdrant_storage/deploy}"
export PORT="${PORT:-7860}"

if [[ ! -f "${QDRANT_PATH}/meta.json" ]]; then
  extra=()
  input_jsonl="${INPUT_JSONL:-data/samples/deploy_msmarco_500.jsonl}"
  if [[ -f "${input_jsonl}" ]]; then
    extra+=(--input-jsonl "${input_jsonl}")
  fi
  python scripts/build_streaming_index.py \
    --language "${DATASET_LANGUAGE:-hi}" \
    --split "${DATASET_SPLIT:-validation}" \
    --records "${DATASET_RECORDS:-500}" \
    --max-chunks "${DATASET_CHUNKS:-750}" \
    --qdrant-path "${QDRANT_PATH}" \
    --recreate \
    "${extra[@]}"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
