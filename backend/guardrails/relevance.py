"""Off-topic / weak-retrieval guard."""

from __future__ import annotations

import re
from typing import Any

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
    "ક્યાં", "છે", "એક",
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


def coverage(query: str, hits: list[dict[str, Any]], k: int = 5) -> float:
    q = _content_tokens(query)
    if not q:
        return 0.0
    ctx: set[str] = set()
    for h in hits[:k]:
        ctx |= _content_tokens(f"{h.get('text') or ''} {h.get('parent_text') or ''}")
    return len(q & ctx) / len(q)


def should_refuse(
    hits: list[dict[str, Any]],
    threshold: float,
    query: str = "",
) -> tuple[bool, float, str]:
    if query and any(p.search(query) for p in OFFTOPIC):
        return True, 0.0, REFUSAL
    score = coverage(query, hits) if query else 0.0
    if not hits or score < threshold:
        return True, score, REFUSAL
    return False, score, ""
