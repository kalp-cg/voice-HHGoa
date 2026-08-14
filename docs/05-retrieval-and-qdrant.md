# 05 — Retrieval & Qdrant

## Not simple vector search

Too basic for this competition:

```text
query → embedding → cosine top-5
```

## Target retrieval stack

```text
QUERY
  ├── Dense search
  └── BM25 / sparse search
        │
        ▼
   Rank fusion (RRF)
        │
     Top 20
        │
        ▼
     Reranker
        │
     Top 3–5
```

Qdrant supports hybrid dense+sparse, RRF-style fusion, multi-stage retrieval, and metadata filtering.

Refs:

- [Hybrid Search](https://qdrant.tech/documentation/search/text-search/hybrid-search/)
- [Hybrid + reranking](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/)
- [Local quickstart](https://qdrant.tech/documentation/quick-start/)

## Why Qdrant fits

- Dense vectors
- Sparse vectors
- Metadata / payload
- Filtering
- Hybrid + multi-stage
- Runs locally in Docker/Podman with mounted `qdrant_storage/`

## Two-stage pattern (latency)

1. Cheap retrieve over large corpus → small candidate set (e.g. 20)
2. Expensive reranker only on candidates → top 3–5

Never rerank millions of docs.

## Milestone order for retrieval

1. Mini-index (10k) + dense-only smoke test
2. Add BM25 / sparse
3. Hybrid fusion (RRF)
4. Reranker on top-20
5. Only then wire LLM + voice
