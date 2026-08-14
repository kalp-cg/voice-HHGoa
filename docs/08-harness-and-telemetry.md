# 08 — Orchestration Harness & Telemetry

## Requirement

Pipeline must run inside a **proper harness**: structured orchestration, retries, structured I/O, error recovery.

Not:

```python
answer = llm(prompt)
```

## Stage graph

```text
Request
  → Validate
  → STT (if voice)
  → Query Classifier / Router
  → Retriever (hybrid)
  → Reranker
  → Generator
  → Grounding Validator
  → Response
```

Every stage returns structured data.

## Example response envelope

```json
{
  "request_id": "abc123",
  "transcript": "What is ...?",
  "language": "en",
  "retrieval": {
    "candidates": 20,
    "selected": 5
  },
  "answer": "...",
  "grounded": true,
  "latency_ms": {
    "stt": 151,
    "embedding": 12,
    "retrieval": 8,
    "reranking": 17,
    "generation": 41,
    "total_rag": 78
  }
}
```

## Implementation home

`backend/orchestration/pipeline.py` owns stage sequencing, timeouts/retries, and aggregating telemetry from `backend/core/telemetry.py`.
