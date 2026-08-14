"""Fast extractive answer from the top reranked passage."""

from __future__ import annotations

from typing import Any

from backend.generation.prompts import REFUSAL
from ingestion.chunking.sentence import split_sentences


def extractive_answer(query: str, hits: list[dict[str, Any]]) -> str:
    if not hits:
        return REFUSAL
    text = (hits[0].get("parent_text") or hits[0].get("text") or "").strip()
    if not text:
        return REFUSAL
    sents = split_sentences(text)
    if not sents:
        return text[:400]
    return " ".join(sents[:2])
