"""Sentence-level chunking."""

from __future__ import annotations

import re

_SENT_SPLIT = re.compile(r"(?<=[.!?।॥])\s+")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def sentence_chunks(text: str, min_chars: int = 40) -> list[str]:
    sents = split_sentences(text)
    if not sents:
        return [text] if len(text) >= min_chars else []
    # Merge tiny sentences with the next one
    chunks: list[str] = []
    buf = ""
    for s in sents:
        if not buf:
            buf = s
        elif len(buf) < min_chars:
            buf = f"{buf} {s}"
        else:
            chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    return chunks
