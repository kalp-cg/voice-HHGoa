"""Rerank hybrid candidates with a lexical + dense blend (CPU, no Torch)."""

from __future__ import annotations

import math
import re
from typing import Any

from backend.core.translit import (
    any_fuzzy_match,
    fold_roman,
    fuzzy_key,
    is_mixed_script,
    romanize_token,
    scripts_in,
)
from backend.retrieval.dedupe import dedupe_hits

_CAP = re.compile(r"\b[A-Z][A-Za-z]{2,}\b")
_TOKEN = re.compile(r"[\w\u0900-\u0D7F\u0600-\u06FF]+", re.UNICODE)


_STOP = {
    "the", "a", "an", "is", "are", "of", "in", "to", "and", "or", "for", "that",
    "this", "it", "on", "with", "as", "be", "was", "were", "by", "what", "where",
    "who", "how", "when", "which", "does", "do", "did", "can", "you", "me",
    "please", "tell", "located",
    "कहाँ", "कहा", "क्या", "कौन", "कैसे", "क्यों", "है", "हैं", "का", "की", "के",
    "में", "से", "और", "कुत्र", "अस्ति", "आहे", "कुठे",
    "কোথায়", "কত", "আছে", "একটি", "এবং",
    "எங்கே", "என்ன", "உள்ளது", "ஒரு",
    "ఎక్కడ", "ఉంది", "ఒక",
    "ಎಲ್ಲಿದೆ", "ಇದೆ", "ಒಂದು",
    "എവിടെയാണ്", "ആണ്", "ഒരു",
    "ક્યાં", "કયાં", "છે", "એક",
    "کہاں", "ہے", "ایک",
    "छ", "हो",
    "କେଉଁଠି", "ଅଛି", "ଏକ",
    "ਕਿੱਥੇ", "ਹੈ", "ਇੱਕ",
}


# A question word keeps its job when speech recognition writes it in the wrong
# script, so stopwords are matched on sound rather than spelling.
_ROMAN_STOP = frozenset(fold_roman(romanize_token(word)) for word in _STOP) - {""}


def _tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in _TOKEN.findall(text or "")
        if len(t) > 1
        and t.lower() not in _STOP
        and fold_roman(romanize_token(t.lower())) not in _ROMAN_STOP
    }


def _lexical_score(query: str, text: str, cross_script: bool = False) -> float:
    q = _tokens(query)
    d = _tokens(text)
    if not q or not d:
        return 0.0
    matched = len(q & d)
    # Without this, the passage that answers a mixed-script question scores the
    # same zero overlap as every unrelated passage in the same language.
    if cross_script and matched < len(q):
        buckets: dict[str, list[str]] = {}
        for token in d:
            roman = romanize_token(token)
            if roman:
                buckets.setdefault(fuzzy_key(roman), []).append(roman)
        for token in q - d:
            target = romanize_token(token)
            if len(target) >= 3 and any_fuzzy_match(target, buckets):
                matched += 1
    return matched / len(q)


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
    query_scripts = scripts_in(query)
    ranked = []
    for hit in unique:
        row = dict(hit)
        text = f"{hit.get('text') or ''} {hit.get('parent_text') or ''}"
        # A passage written in another script shares no characters with the
        # query, so plain overlap would score it the same as an unrelated one.
        cross_script = is_mixed_script(query) or not (
            scripts_in(text) <= query_scripts
        )
        lex = _lexical_score(query, text, cross_script=cross_script)
        orig = float(hit.get("orig_score") or 0.0)
        dense_bonus = 0.2 * orig if 0 < orig <= 1.5 else 0.0
        rrf = float(hit.get("rrf_score") or 0.0)
        proper = {m.lower() for m in _CAP.findall(query)}
        proper_bonus = 0.0
        if proper:
            blob = text.lower()
            proper_bonus = sum(1.0 for p in proper if p in blob) / len(proper)
        source_query = str(hit.get("_source_query") or "")
        query_tokens = _tokens(query)
        source_tokens = _tokens(source_query)
        exact_query_bonus = (
            1.0
            if source_query and query_tokens and query_tokens == source_tokens
            else 0.0
        )
        score = (
            lex
            + dense_bonus
            + 0.15 * rrf
            + 1.25 * proper_bonus
            + exact_query_bonus
        )
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
