---
title: Voice RAG Goa
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
startup_duration_timeout: 30m
short_description: Fast grounded voice RAG over MSMARCO-XI
---

# Voice RAG Goa

Voice-first RAG: **microphone → ElevenLabs STT → hybrid retrieval → rerank → grounded answer**, with multi-strategy chunking, a structured harness, guardrails, and P50/P70/P100 latency analytics.

**Live demo:** https://voice-hhgoa.onrender.com (free tier — first request after idle takes ~30 s to wake)

**Hardware:** RTX 3050 6 GB + 16 GB RAM  
**Deadline:** 22 Aug 2026, 11:59 PM · tag `#RAGInGoa`

## What is implemented

- ElevenLabs Scribe v2 Realtime STT (browser mic, single-use token)
- MSMARCO-XI Hindi validation shard sample (10k records, not the 55.6 GB dump)
- Multi-strategy chunks (sentence / sliding / semantic / parent-child), compacted for the index
- Dense + BM25 + RRF hybrid retrieval, lexical/dense rerank to top 5
- Retrieval-grounded answers with **no LLM in the hot path** (warm RAG **P50 53 ms / P70 73 ms / P100 160 ms** on 190 queries)
- Optional local generation via Ollama `qwen2.5:1.5b`, off by default and excluded from the latency claim
- Guardrails: unsafe input, off-topic, retrieval coverage, post-generation grounding
- Demo UI with transcript, answer, sources, grounded/refused, stage timings

## Run locally

```bash
cd /home/kalppatel/Desktop/voice-HHgoa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# .env must contain ELEVENLABS_API_KEY=...
python scripts/rebuild_index.py --recreate
./scripts/start.sh
```

Open **http://127.0.0.1:8000**

- **Start mic** → speak → committed transcript is answered automatically
- Or type a question and click **Ask**

No LLM runs in this path. Ollama is not required.

Startup warms embeddings + BM25 (~3–4 s). First query after that should be in the ~70–140 ms RAG range.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Index + Ollama readiness |
| GET | `/api/voice/scribe-token` | Single-use STT token |
| POST | `/api/query` | Full harness (defaults to the no-LLM fast path) |
| POST | `/api/query/fast` | Force the no-LLM path |
| POST | `/api/retrieve/hybrid` | Dense+BM25+RRF+rerank only |

## Benchmark (2026-08-14, 190 queries, fast mode, after warmup)

| Stage | P50 ms | P70 ms | P100 ms |
|-------|--------|--------|---------|
| Embedding | 10.2 | 13.6 | 36.8 |
| Dense | 23.7 | 29.8 | 70.7 |
| BM25 | 17.3 | 25.3 | 85.4 |
| Fusion | 0.1 | 0.1 | 3.0 |
| Rerank | 1.0 | 1.1 | 8.0 |
| Generation (extractive) | 0.0 | 0.0 | 0.0 |
| **RAG total** | **53.1** | **73.4** | **159.5** |

- Adversarial refusal rate: **1.0** (weather / joke / cricket 2026 / bomb)
- Recall@5 / MRR on held-out MSMARCO query_ids: 0.26 / 0.23 (index is a compact 12k-chunk slice)
- STT (~150 ms class) is **not** included in RAG totals
- Assignment target: RAG path **&lt;200 ms**. Warm P50/P70/P100 all meet it.

Re-run: `./scripts/benchmark.sh`

## Dataset policy

Do **not** download the full 55.6 GB repo. Stream shards with a cap:

```bash
python scripts/build_streaming_index.py --split train --language hi --records 50000 --max-chunks 60000 --recreate
```

The current demo index is bootstrap + 10k Hindi records → **11,627–12,000 chunks**.

Hub streaming of `train/hintrain.parquet` for a 50k cap was **attempted and blocked** here (DNS / hang on `hf://`). Use the local JSONL path, which was verified end-to-end:

```bash
python scripts/build_streaming_index.py \
  --input-jsonl data/processed/msmarco_xi_hi_10k.jsonl \
  --records 10000 --max-chunks 12000 --recreate
```

## Deploy (container)

```bash
docker build -t voice-rag-goa .
docker run --rm -p 7860:7860 \
  -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  -e QDRANT_PATH=/data \
  -v "$PWD/qdrant_storage/local:/data:Z" \
  voice-rag-goa
```

### Deploy on Render

Live: https://voice-hhgoa.onrender.com

1. https://dashboard.render.com → **New +** → **Web Service**
2. Connect `kalp-cg/voice-HHGoa`, runtime **Docker**, branch `main`
3. Add env var `ELEVENLABS_API_KEY` (secret)
4. Create service and wait for first build
5. Use the Render HTTPS URL as your submission live link

Render Free gives 512 MB RAM, which is not enough to hold the FastEmbed ONNX
model, so the deployed image runs `RETRIEVAL_MODE=sparse`: BM25 + rerank +
guardrails over a balanced 2,171-chunk / 15-language index baked at build time
(123 MB container memory in the local deployment check). Dense
and hybrid endpoints return 501 there and answer normally on any host with
≥2 GB RAM. Local runs stay full hybrid.

Details: [docs/15-submission-kit.md](./docs/15-submission-kit.md)

Videos and `#RAGInGoa` posts are still yours.

## Docs

Index: [docs/README.md](./docs/README.md) · milestones: [docs/12-milestones-roadmap.md](./docs/12-milestones-roadmap.md)

## Submission (remaining user actions)

The public GitHub repository and live URL are ready. Record the two required
videos, publish them with `#RAGInGoa`, and submit the form before the deadline.
