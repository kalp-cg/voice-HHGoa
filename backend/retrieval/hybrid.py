"""Hybrid dense + BM25 fusion via Reciprocal Rank Fusion (RRF)."""

from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
    limit: int = 20,
    id_key: str = "chunk_id",
) -> list[dict[str, Any]]:
    """
    RRF score for doc d = sum 1 / (k + rank_i(d)) across lists.
    Higher is better. Ties broken by first-seen order.
    """
    scores: dict[str, float] = {}
    payloads: dict[str, dict[str, Any]] = {}

    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            doc_id = str(hit.get(id_key) or "")
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in payloads:
                body = dict(hit)
                body["orig_score"] = float(hit.get("score") or 0.0)
                payloads[doc_id] = body

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    out: list[dict[str, Any]] = []
    for doc_id, score in ordered:
        row = dict(payloads[doc_id])
        row["score"] = float(score)
        row["rrf_score"] = float(score)
        out.append(row)
    return out
