"""Rerank hybrid candidates with a lexical + dense blend (CPU, no Torch)."""

from __future__ import annotations

import math
import re
from typing import Any

from backend.retrieval.dedupe import dedupe_hits

_CAP = re.compile(r"\b[A-Z][A-Za-z]{2,}\b")
_TOKEN = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)


_STOP = {
    "the", "a", "an", "is", "are", "of", "in", "to", "and", "or", "for", "that",
    "this", "it", "on", "with", "as", "be", "was", "were", "by", "what", "where",
    "who", "how", "when", "which", "does", "do", "did", "can", "you", "me",
    "please", "tell",
}


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text or "") if t.lower() not in _STOP and len(t) > 1}


def _lexical_score(query: str, text: str) -> float:
    q = _tokens(query)
    d = _tokens(text)
    if not q or not d:
        return 0.0
    return len(q & d) / len(q)


def rerank(
    query: str,
    hits: list[dict[str, Any]],
    top_k: int = 5,
    model_name: str = "",  # unused; kept for API compatibility
) -> list[dict[str, Any]]:
    """
    Fast CPU reranker: 55% normalized retrieval score + 45% query-term overlap.
    Avoids Torch / ONNX cross-encoders on the 6 GB / Python 3.14 stack.
    """
    unique = dedupe_hits(hits)
    if not unique:
        return []
    ranked = []
    for hit in unique:
        row = dict(hit)
        text = f"{hit.get('text') or ''} {hit.get('parent_text') or ''}"
        lex = _lexical_score(query, text)
        orig = float(hit.get("orig_score") or 0.0)
        dense_bonus = 0.2 * orig if 0 < orig <= 1.5 else 0.0
        rrf = float(hit.get("rrf_score") or 0.0)
        proper = {m.lower() for m in _CAP.findall(query)}
        proper_bonus = 0.0
        if proper:
            blob = text.lower()
            proper_bonus = sum(1.0 for p in proper if p in blob) / len(proper)
        score = lex + dense_bonus + 0.15 * rrf + 1.25 * proper_bonus
        row["rerank_score"] = score
        row["score"] = score
        ranked.append(row)
    ranked.sort(key=lambda h: h["rerank_score"], reverse=True)
    return ranked[:top_k]


def relevance_score(hits: list[dict[str, Any]]) -> float:
    if not hits:
        return 0.0
    top = float(hits[0].get("rerank_score") or hits[0].get("score") or 0.0)
    if top <= 1.0:
        return max(0.0, min(1.0, top))
    return 1.0 / (1.0 + math.exp(-top / 8.0))
