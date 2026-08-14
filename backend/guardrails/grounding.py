"""Post-generation grounding: answer must overlap retrieved context."""

from __future__ import annotations

import re
from typing import Any

from backend.generation.prompts import REFUSAL

_TOKEN = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)

STOP = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "of",
    "in",
    "to",
    "and",
    "or",
    "for",
    "that",
    "this",
    "it",
    "on",
    "with",
    "as",
    "be",
    "was",
    "were",
    "by",
}


def _tokens(text: str) -> set[str]:
    return {
        t.lower()
        for t in _TOKEN.findall(text or "")
        if t.lower() not in STOP and len(t) > 1
    }


def overlap_ratio(answer: str, context: str) -> float:
    a = _tokens(answer)
    c = _tokens(context)
    if not a or not c:
        return 0.0
    return len(a & c) / len(a)


def context_from_hits(hits: list[dict[str, Any]]) -> str:
    parts = []
    for h in hits:
        parts.append(str(h.get("parent_text") or h.get("text") or ""))
    return "\n".join(parts)


def verify_grounding(
    answer: str,
    hits: list[dict[str, Any]],
    min_overlap: float,
) -> tuple[bool, float, str]:
    if not answer.strip() or answer.strip() == REFUSAL:
        return True, 1.0, answer
    ctx = context_from_hits(hits)
    ratio = overlap_ratio(answer, ctx)
    if ratio < min_overlap:
        return False, ratio, REFUSAL
    return True, ratio, answer
