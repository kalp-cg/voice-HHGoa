# Measured latency (fast path)

Date: 2026-08-14  
N = 190 queries (`evaluation/queries.jsonl`) after one warmup  
Mode: extractive / fast. STT excluded.

**Latest full-hybrid run** (`qdrant_storage/local`, ~12k chunks):

| Stage | P50 | P70 | P100 |
|-------|-----|-----|------|
| Embedding | 11.1 | 15.8 | 38.1 |
| Dense | 34.4 | 41.0 | 95.7 |
| BM25 | 34.1 | 52.9 | 96.6 |
| Fusion | 0.1 | 0.1 | 6.2 |
| Rerank | 0.9 | 1.2 | 16.5 |
| Generation | 0.0 | 0.0 | 0.0 |
| RAG total | **93.2** | **118.7** | **175.5** |

Earlier same-day demo-index run: RAG total **P50 53.1 / P70 73.4 /
P100 159.5**. Runtime load changes the absolute numbers; both measured runs
stay below 200 ms at P100.

**Rebuilt isolated index** (`qdrant_storage/scaled-10k`, 11,627 chunks from all
10,005 records): RAG total **P50 76.6 / P70 97.7 / P100 184.4**.

Adversarial refusal rate: **1.0**  
Latest Recall@5: 0.328 · MRR: 0.265

The memory-capped sparse deployment is evaluated separately over its balanced
sample: **1,965/1,965 paired queries grounded**, with **1,965/1,965 same-language
top hits**. Reproduce with `scripts/evaluate_sparse_sample.py`.

Assignment target is **&lt;200 ms** for retrieval → answer. Both measured P100s meet it.

STT (~150 ms class, ElevenLabs) is **not** included in these totals. Full voice wall-clock is STT + RAG.

Ollama generation is optional, unused in the demo path, and typically multiple seconds.
