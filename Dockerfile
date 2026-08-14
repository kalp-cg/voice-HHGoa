FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    QDRANT_PATH=qdrant_storage/deploy \
    RETRIEVAL_MODE=sparse \
    DEFAULT_ANSWER_MODE=fast \
    SKIP_STARTUP_WARMUP=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    MALLOC_ARENA_MAX=2

WORKDIR /app

COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY backend backend
COPY frontend frontend
COPY ingestion ingestion
COPY retrieval retrieval
COPY scripts scripts
COPY data/samples data/samples

# Prebuild a tiny BM25 chunk store at image build time (no ONNX model).
RUN python scripts/build_sparse_deploy_index.py \
      --input-jsonl data/samples/deploy_msmarco_multilingual.jsonl \
      --no-bootstrap \
      --records 80 \
      --max-chunks 250 \
      --record-batch 16 \
      --output qdrant_storage/deploy/chunks.jsonl \
    && chmod +x scripts/deploy_start.sh

EXPOSE 7860
CMD ["./scripts/deploy_start.sh"]
