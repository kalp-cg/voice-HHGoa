"""Parent/child chunking: search children, keep parent for context."""

from __future__ import annotations

from dataclasses import dataclass

from ingestion.chunking.sentence import sentence_chunks
from ingestion.chunking.semantic import semantic_chunks


@dataclass
class ParentChildChunk:
    parent_id: str
    parent_text: str
    child_id: str
    child_text: str
    child_index: int


def parent_child_chunks(
    parent_id: str,
    parent_text: str,
    child_strategy: str = "sentence",
) -> list[ParentChildChunk]:
    if child_strategy == "semantic":
        children = semantic_chunks(parent_text)
    else:
        children = sentence_chunks(parent_text)

    if not children:
        children = [parent_text]

    out: list[ParentChildChunk] = []
    for i, child in enumerate(children):
        out.append(
            ParentChildChunk(
                parent_id=parent_id,
                parent_text=parent_text,
                child_id=f"{parent_id}::c{i}",
                child_text=child,
                child_index=i,
            )
        )
    return out
