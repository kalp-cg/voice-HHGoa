# Voice RAG Goa — Documentation Index

Hackathon / assignment project: **voice input → STT → hybrid retrieval → grounded answer**, with multi-strategy chunking, latency analytics (P50/P70/P100), orchestration harness, and guardrails.

**Hardware target:** RTX 3050 6 GB VRAM + 16 GB RAM  
**Deadline:** August 22, 2026, 11:59 PM  
**Deliverables:** GitHub repo, live demo link, two videos, promotion posts with `#RAGInGoa`

## Read in this order

| Doc | Purpose |
|-----|---------|
| [01-product-overview.md](./01-product-overview.md) | What we are building and why |
| [02-architecture.md](./02-architecture.md) | Online vs offline pipelines |
| [03-dataset-and-ingestion.md](./03-dataset-and-ingestion.md) | MSMARCO-XI streaming, scale phases |
| [04-chunking-strategies.md](./04-chunking-strategies.md) | Strategies A–E |
| [05-retrieval-and-qdrant.md](./05-retrieval-and-qdrant.md) | Dense + BM25 + RRF + rerank |
| [06-voice-stt-elevenlabs.md](./06-voice-stt-elevenlabs.md) | ElevenLabs Scribe v2 Realtime |
| [07-llm-and-guardrails.md](./07-llm-and-guardrails.md) | Generation + 4 guardrails |
| [08-harness-and-telemetry.md](./08-harness-and-telemetry.md) | Orchestration, structured I/O |
| [09-latency-and-benchmarking.md](./09-latency-and-benchmarking.md) | P50/P70/P100, metrics |
| [10-project-structure.md](./10-project-structure.md) | Repo layout |
| [11-environment-and-secrets.md](./11-environment-and-secrets.md) | Stack, `.env`, gitignore |
| [12-milestones-roadmap.md](./12-milestones-roadmap.md) | Build order (Step 1 → 22) |
| [13-delivery-checklist.md](./13-delivery-checklist.md) | Final submission checklist |
| [14-measured-latency.md](./14-measured-latency.md) | P50/P70/P100 from 190-query run |
| [15-submission-kit.md](./15-submission-kit.md) | Video scripts, captions, public demo, final form checklist |
| [16-demo-testing-and-video-guide.md](./16-demo-testing-and-video-guide.md) | Verified multilingual questions and recording checklist |

## Non-negotiables

1. **Do not download all 55.6 GB** of MSMARCO-XI. Stream, sample, scale.
2. Build **milestone by milestone**.
3. Measure latency honestly: STT is separate from RAG; warm RAG P50/P70/P100 are under 200 ms.
4. Never commit dataset, embeddings, Qdrant storage, or API keys.
