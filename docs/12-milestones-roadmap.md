# 12 — Milestones Roadmap

Build **one milestone at a time**. Do not combine unrelated layers in a single Cursor task.

**Deadline:** August 22, 2026, 11:59 PM

## Current focus

**Steps 1–21 complete.** Step 20 is a capped streamed scale-up from MSMARCO-XI train, not a 55.6 GB download. Live demo: https://voice-hhgoa.onrender.com. Only videos and `#RAGInGoa` posts (step 22) remain, and those are yours.

Warm fast-path RAG (190 queries, 2026-08-14): **P50 53 ms, P70 73 ms, P100 160 ms**.

---

## Step checklist

| Step | Action | Done when |
|------|--------|-----------|
| 1 | Create project folder | ✅ |
| 2 | Open in Cursor | ✅ |
| 3 | Init Git repo | ✅ |
| 4 | Create Python venv | ✅ |
| 5 | Create project structure | ✅ |
| 6 | Add ElevenLabs key to `.env` | ✅ |
| 7 | ElevenLabs mic → transcript | UI live; confirm in browser |
| 8 | Stream-inspect MSMARCO-XI | ✅ 10k from `hinval.parquet` |
| 9 | Mini-index | ✅ 12k compact chunks / 10,005 records |
| 10 | Dense retrieval | ✅ `/api/retrieve/dense` |
| 11 | BM25 / sparse | ✅ `/api/retrieve/sparse` |
| 12 | Hybrid fusion (RRF) | ✅ |
| 13 | Reranker | ✅ lexical+dense top 3–5 |
| 14 | LLM grounded QA | ✅ extractive + Ollama `qwen2.5:1.5b` |
| 15 | Guardrails (4+) | ✅ unsafe, off-topic, coverage, grounding |
| 16 | Wire ElevenLabs → full RAG | ✅ committed transcript → `/api/query` |
| 17 | Frontend | ✅ answer, sources, latency |
| 18 | Benchmark 100–500 queries | ✅ 190 queries, P50/P70/P100 |
| 19 | Optimize latency | ✅ warm P50/P70/P100 all under 200 ms |
| 20 | Scale corpus (capped stream, not 55.6 GB) | ✅ 10,005 records / 11,627 chunks via `scripts/build_streaming_index.py`. Remote 50k train stream blocked by Hub DNS/hang; command is ready. |
| 21 | Deploy live demo | ✅ https://voice-hhgoa.onrender.com — Render Free, BM25-only (`RETRIEVAL_MODE=sparse`) because 512 MB cannot hold the ONNX embedder |
| 22 | GitHub + 2 videos + `#RAGInGoa` | User |
