# 11 — Environment & Secrets

## Host stack (Fedora)

- Python 3.11 or 3.12
- `uv` or `venv`
- Docker or Podman (Qdrant)
- Git
- CUDA-compatible PyTorch (for embed/rerank)
- Cursor

```bash
python -m venv .venv
source .venv/bin/activate
```

## `.env` (local only)

```text
ELEVENLABS_API_KEY=YOUR_KEY
QDRANT_URL=http://localhost:6333
LLM_API_KEY=YOUR_KEY
EMBEDDING_MODEL=...
RERANKER_MODEL=...
```

Use `.env.example` with empty placeholders for the repo.

## `.gitignore` must include

```text
.env
__pycache__/
.venv/
qdrant_storage/
data/raw/
data/processed/
*.parquet
*.jsonl
*.bin
*.safetensors
```

(Keep tiny tracked samples under something like `evaluation/fixtures/` if needed — not bulk dumps.)

## GPU usage policy

| Workload | Device |
|----------|--------|
| Embeddings | GPU |
| Reranker | GPU |
| Local LLM (optional later) | GPU |
| Qdrant / BM25 / FastAPI / ingestion orchestration | CPU/RAM |
| ElevenLabs + primary LLM | Cloud API |

## Qdrant

Run via `docker-compose.yml` with persistent volume → `./qdrant_storage`.
