# 13 — Delivery Checklist

## Assignment deadline

**August 22, 2026 — 11:59 PM**

## Required deliverables

- [ ] Public **GitHub** repository (code + docs; no secrets/data dumps) — `gh` token for `kalp-cg` is invalid
- [ ] **Live working link** (demo URL) — Docker image `voice-rag-goa:test` builds and serves locally on `:7861`; public host still needed
- [ ] **Two videos** (as required by assignment brief)
- [ ] Promotion posts with **`#RAGInGoa`**

## Technical completeness

- [x] Voice → ElevenLabs STT → transcript
- [x] Hybrid retrieval (dense + BM25/sparse + fusion)
- [x] Reranker
- [x] Grounded answers (extractive + optional Ollama)
- [x] Multiple chunking strategies (A–E)
- [x] Guardrails (≥4): off-topic, confidence, grounded prompt, post-check
- [x] Orchestration harness with structured I/O + telemetry
- [x] Latency analytics: P50 / P70 / P100 for key stages (190 queries; P100 160 ms)
- [x] Honest reporting of STT vs RAG vs full-pipeline latency

## Repo hygiene

- [x] `.env` gitignored; `.env.example` present
- [x] No MSMARCO-XI full dump / embeddings / `qdrant_storage` in Git
- [x] README explains setup, demo, and architecture (link to `docs/`)
- [x] `Dockerfile` + `scripts/deploy_start.sh` for container/Space-style deploy (embedded Qdrant default)

## Demo polish

- [x] Hold-to-speak (or equivalent) mic UX
- [x] Show transcript, answer, sources, grounded flag
- [x] Dev/latency panel for stage timings

## Engineering story to tell

We streamed MSMARCO-XI, scaled from 10k upward, used hybrid retrieval + rerank, measured latency honestly, and guarded against ungrounded answers — instead of dumping 56 GB into RAM.
