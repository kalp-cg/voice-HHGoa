# 13 — Delivery Checklist

## Assignment deadline

**August 22, 2026 — 11:59 PM**

## Required deliverables

- [x] Public **GitHub** repository (code + docs; no secrets/data dumps) — https://github.com/kalp-cg/voice-HHGoa
- [x] **Live working link** — https://voice-hhgoa.onrender.com
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
- [x] One committed question per mic session; partial/noisy transcripts cannot auto-send
- [x] Automatic language detection with a manual override

## Verified deployment profile

- [x] Render Free stays within 512 MB using BM25-only retrieval
- [x] Balanced live sample: 210 records → 300 chunks across 15 languages
- [x] Paired-query sparse evaluation: 210/210 grounded answers
- [x] Automatic-language demo check: 15/15 Goa questions
- [x] Local full hybrid remains available on hardware with ≥2 GB RAM

## Engineering story to tell

We streamed MSMARCO-XI, scaled from 10k upward, used hybrid retrieval + rerank, measured latency honestly, and guarded against ungrounded answers — instead of dumping 56 GB into RAM.
