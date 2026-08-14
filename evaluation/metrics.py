"""Evaluation metrics: percentiles, Recall@K, MRR."""

from __future__ import annotations

from backend.core.telemetry import percentiles


def recall_at_k(hits: list[dict], gold_query_id, k: int = 5) -> float:
    if gold_query_id is None:
        return 0.0
    top = hits[:k]
    return 1.0 if any(str(h.get("query_id")) == str(gold_query_id) for h in top) else 0.0


def mrr(hits: list[dict], gold_query_id) -> float:
    if gold_query_id is None:
        return 0.0
    for i, h in enumerate(hits, start=1):
        if str(h.get("query_id")) == str(gold_query_id):
            return 1.0 / i
    return 0.0


def summarize_latencies(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    out: dict[str, dict[str, float]] = {}
    for key in sorted(keys):
        vals = [float(r[key]) for r in rows if key in r]
        out[key] = percentiles(vals)
    return out
