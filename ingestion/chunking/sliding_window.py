"""Fixed / sliding window over sentences."""

from __future__ import annotations

from ingestion.chunking.sentence import split_sentences


def sliding_window_chunks(
    text: str,
    window: int = 3,
    stride: int = 1,
) -> list[str]:
    sents = split_sentences(text)
    if not sents:
        return [text] if text.strip() else []
    if len(sents) <= window:
        return [" ".join(sents)]

    chunks: list[str] = []
    for i in range(0, len(sents) - window + 1, stride):
        chunks.append(" ".join(sents[i : i + window]))
    # Tail if stride skipped end
    last = " ".join(sents[-window:])
    if chunks[-1] != last:
        chunks.append(last)
    return chunks
