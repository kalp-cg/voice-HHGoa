# 01 — Product Overview

## What we are making

A **voice-first RAG** application for the Goa assignment:

```text
USER speaks
  → WEB FRONTEND (microphone UI)
  → ELEVENLABS Scribe v2 Realtime STT
  → QUERY ROUTER (language / intent / validation)
  → HYBRID RETRIEVER (Dense + BM25)
  → Top 20 candidates
  → RERANKER → Top 3–5
  → LLM (grounded QA)
  → GUARDRAILS (grounding / confidence / off-topic)
  → ANSWER
```

The backend records **latency for every stage**.

## Assignment requirements (must ship)

| Requirement | Our approach |
|-------------|--------------|
| Voice input → STT → retrieval → answer | ElevenLabs + FastAPI pipeline |
| Multiple chunking strategies | Sentence, sliding, semantic, parent/child, metadata-aware |
| Latency target & honesty | Measure RAG stages; STT ~150 ms alone — do not claim full voice→answer <200 ms without evidence |
| P50 / P70 / P100 | Benchmark harness over 100–500 queries |
| Orchestration harness | Structured stages, retries, typed I/O, error recovery |
| Guardrails | Off-topic, retrieval confidence, grounded prompt, post-gen verification |

## Two mental models

### Offline (before demo)

MSMARCO-XI → stream → clean → dedupe → chunk → embed → Qdrant

### Online (when user asks)

Voice → STT → query processing → embed → hybrid search → rerank → LLM → guardrail → answer

The raw 55.6 GB dataset is **ingestion fuel only**. Users never load it directly.

## Hardware reality

```text
RAM       16 GB
VRAM       6 GB (RTX 3050)
Dataset   ~55.6 GB (MSMARCO-XI)
```

Therefore: stream data, start with 10k–50k records, use compact embeddings + quantization, run Qdrant locally, put embedding/reranker on GPU selectively, use API LLM first.
