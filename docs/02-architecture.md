# 02 — Architecture

## Final online architecture

```text
┌───────────────┐
│   Browser     │
│ Microphone    │
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│   ElevenLabs    │
│ Scribe Realtime │
└────────┬────────┘
         │ transcript
         ▼
┌─────────────────┐
│ FastAPI Backend │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Orchestrator│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
Dense Emb   BM25
    │         │
    └────┬────┘
         ▼
  Qdrant Hybrid (RRF)
         │
      Top 20
         │
         ▼
     Reranker
         │
       Top 5
         │
         ▼
        LLM
         │
         ▼
  Grounding Check
    │         │
 grounded   reject
    │
    ▼
 ANSWER
```

## Offline ingestion architecture

```text
MSMARCO-XI (~55.6 GB)
      │
  streaming batches
      │
      ▼
  cleaning → deduplication → language metadata
      │
  multi-strategy chunking
      │
  embeddings (GPU when available)
      │
  Qdrant index (dense + sparse + payload)
```

## Where work runs

| Layer | Runs on |
|-------|---------|
| Embedding model | GPU (RTX 3050) |
| Reranker | GPU |
| Optional small local LLM | GPU (later; API first) |
| Qdrant, BM25, FastAPI, orchestration | CPU / RAM |
| ElevenLabs STT | Cloud API |
| Primary LLM (v1) | Cloud API |

## Why Qdrant

Local Docker/Podman, dense + sparse vectors, metadata filters, hybrid / multi-stage search, RRF-style fusion — matches assignment needs without a giant managed vector DB.
