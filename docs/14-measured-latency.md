# Measured latency (fast path)

Date: 2026-08-14  
N = 190 queries (`evaluation/queries.jsonl`) after one warmup  
Mode: extractive / fast. STT excluded.

**Demo index** (`qdrant_storage/local`, ~12k chunks):

| Stage | P50 | P70 | P100 |
|-------|-----|-----|------|
| Embedding | 10.2 | 13.6 | 36.8 |
| Dense | 23.7 | 29.8 | 70.7 |
| BM25 | 17.3 | 25.3 | 85.4 |
| Fusion | 0.1 | 0.1 | 3.0 |
| Rerank | 1.0 | 1.1 | 8.0 |
| Generation | 0.0 | 0.0 | 0.0 |
| RAG total | **53.1** | **73.4** | **159.5** |

**Rebuilt isolated index** (`qdrant_storage/scaled-10k`, 11,627 chunks from all 10,005 records): RAG total **P50 76.6 / P70 97.7 / P100 184.4**.

Adversarial refusal rate: **1.0**  
Recall@5: 0.263 · MRR: 0.235–0.236

Assignment target is **&lt;200 ms** for retrieval → answer. Both measured P100s meet it.

STT (~150 ms class, ElevenLabs) is **not** included in these totals. Full voice wall-clock is STT + RAG.

Ollama generation is optional, unused in the demo path, and typically multiple seconds.
