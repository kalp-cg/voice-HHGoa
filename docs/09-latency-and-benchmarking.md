# 09 — Latency & Benchmarking

## Required measurements

P50, P70, P100 over a reasonable query set (target **100–500** queries).

Break down by component:

- Embedding
- Retrieval (hybrid)
- Reranker
- LLM
- RAG total
- Full voice pipeline (when STT included)

## Harness artifacts

```text
evaluation/
  queries.jsonl      # 100–500 queries, multi-lang / types
  benchmark.py
  metrics.py
  results/
    benchmark_YYYY-MM-DD.json
```

## Metrics beyond latency

Also track retrieval quality where labels exist:

- Recall@K
- MRR

## Dashboard (frontend / dev panel)

Show per-request and aggregate latency. Numbers in design mocks are **illustrative only** — never claim unmeasured figures.

## Optimization order

1. Make correct
2. Measure honestly
3. Optimize hot stages
4. Scale corpus and re-measure
