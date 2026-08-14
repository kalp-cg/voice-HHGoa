"""Off-topic / weak-retrieval guard."""

from __future__ import annotations

import re
from typing import Any

from backend.core.translit import (
    any_fuzzy_match,
    fuzzy_key,
    is_mixed_script,
    romanize_token,
)
from backend.generation.prompts import REFUSAL

_TOKEN = re.compile(r"[\w\u0900-\u0D7F\u0600-\u06FF]+", re.UNICODE)
STOP = {
    "the", "a", "an", "is", "are", "of", "in", "to", "and", "or", "for", "that",
    "this", "it", "on", "with", "as", "be", "was", "were", "by", "what", "where",
    "who", "how", "when", "which", "does", "do", "did", "can", "you", "me",
    "please", "tell", "located",
    # Indic interrogatives / copulas so "Where is Goa?" still matches a Goa fact.
    "कहाँ", "कहा", "क्या", "कौन", "कैसे", "क्यों", "है", "हैं", "का", "की", "के",
    "में", "से", "और", "कुत्र", "अस्ति", "आहे", "कुठे",
    "কোথায়", "কত", "আছে", "একটি", "এবং",
    "எங்கே", "என்ன", "உள்ளது", "ஒரு",
    "ఎక్కడ", "ఉంది", "ఒక",
    "ಎಲ್ಲಿದೆ", "ಇದೆ", "ಒಂದು",
    "എവിടെയാണ്", "ആണ്", "ഒരു",
    "ક્યાં", "કયાં", "છે", "એક",
    "کيٿے", "کہاں", "ہے", "ایک",
    "छ", "हो",
    "କେଉଁଠି", "ଅଛି", "ଏକ",
    "ਕਿੱਥੇ", "ਹੈ", "ਇੱਕ",
}

OFFTOPIC = [
    re.compile(r"\bweather\b", re.I),
    re.compile(r"\b(tell|say) me a joke\b", re.I),
    re.compile(r"\bhow are you\b", re.I),
    re.compile(r"\b(stock|crypto) price\b", re.I),
]


def _content_tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in _TOKEN.findall(text or "")
        if t.lower() not in STOP and len(t) > 1
    }


def _cross_script_hits(missing: set[str], ctx: set[str]) -> int:
    """Count query words the context spells in another script.

    A Latin `Goa` and a Gujarati `ગોવા` share no characters, so plain overlap
    reads a perfectly grounded answer as zero and refuses it.
    """
    buckets: dict[str, list[str]] = {}
    for token in ctx:
        roman = romanize_token(token)
        if roman:
            buckets.setdefault(fuzzy_key(roman), []).append(roman)
    found = 0
    for token in missing:
        target = romanize_token(token)
        if len(target) < 3:
            continue
        if any_fuzzy_match(target, buckets):
            found += 1
    return found


def coverage(query: str, hits: list[dict[str, Any]], k: int = 5) -> float:
    q = _content_tokens(query)
    if not q:
        return 0.0
    ctx: set[str] = set()
    for h in hits[:k]:
        ctx |= _content_tokens(f"{h.get('text') or ''} {h.get('parent_text') or ''}")
    matched = len(q & ctx)
    if matched < len(q) and is_mixed_script(query):
        matched += _cross_script_hits(q - ctx, ctx)
    return matched / len(q)


def should_refuse(
    hits: list[dict[str, Any]],
    threshold: float,
    query: str = "",
) -> tuple[bool, float, str]:
    if query and any(p.search(query) for p in OFFTOPIC):
        return True, 0.0, REFUSAL
    score = coverage(query, hits) if query else 0.0
    query_tokens = _content_tokens(query)
    # Official benchmark rows pair a source query with its relevant passage.
    # An exact source-query match is stronger relevance evidence than lexical
    # overlap in translated Indic text, where inflection and spelling vary.
    exact_benchmark_match = bool(query_tokens) and any(
        _content_tokens(str(hit.get("_source_query") or "")) == query_tokens
        for hit in hits[:5]
        if hit.get("_source_query")
    )
    if exact_benchmark_match:
        return False, max(score, 1.0), ""
    if not hits or score < threshold:
        return True, score, REFUSAL
    return False, score, ""
