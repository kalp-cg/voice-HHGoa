"""Lightweight semantic chunking via sentence-length + punctuation boundaries."""

from __future__ import annotations

from ingestion.chunking.sentence import split_sentences


def semantic_chunks(
    text: str,
    target_chars: int = 450,
    max_chars: int = 700,
) -> list[str]:
    """
    Group sentences until a soft size target; force split near max.
    Prefer breaks after longer sentences (proxy for topic closure).
    """
    sents = split_sentences(text)
    if not sents:
        return [text] if text.strip() else []

    chunks: list[str] = []
    buf: list[str] = []
    size = 0

    for s in sents:
        add = len(s) + (1 if buf else 0)
        if buf and size + add > max_chars:
            chunks.append(" ".join(buf))
            buf, size = [s], len(s)
            continue
        buf.append(s)
        size += add
        if size >= target_chars and len(s) > 80:
            chunks.append(" ".join(buf))
            buf, size = [], 0

    if buf:
        chunks.append(" ".join(buf))
    return chunks
