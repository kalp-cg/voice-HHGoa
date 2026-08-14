"""Chunk strategy registry used during ingestion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from ingestion.chunking.parent_child import parent_child_chunks
from ingestion.chunking.semantic import semantic_chunks
from ingestion.chunking.sentence import sentence_chunks
from ingestion.chunking.sliding_window import sliding_window_chunks
from ingestion.deduplicate import PassageDeduper

ChunkStrategy = Literal[
    "sentence",
    "sliding",
    "semantic",
    "parent_child",
]


@dataclass
class ChunkDoc:
    chunk_id: str
    text: str
    parent_text: str
    chunk_type: str
    language: str
    source_lang: str
    target_lang: str
    query_id: Any
    query_type: str
    passage_lang: str  # english | translated
    parent_id: str
    source: str = "MSMARCO-XI"

    def payload(self) -> dict[str, Any]:
        return asdict(self)


def _passages_from_record(rec: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (passage_lang, text) pairs; prefer selected passages when marked."""
    selected = rec.get("is_selected") or []
    pairs: list[tuple[str, str]] = []

    eng = rec.get("english_passages") or []
    tr = rec.get("translated_passages") or []

    indices = list(range(max(len(eng), len(tr))))
    if selected and any(int(x) == 1 for x in selected if x is not None):
        prefer = [i for i, flag in enumerate(selected) if int(flag) == 1]
        if prefer:
            indices = prefer

    for i in indices:
        if i < len(eng) and eng[i]:
            pairs.append(("english", eng[i]))
        if i < len(tr) and tr[i]:
            pairs.append(("translated", tr[i]))

    # Fallback: take first few of each if nothing selected
    if not pairs:
        for t in eng[:3]:
            pairs.append(("english", t))
        for t in tr[:3]:
            pairs.append(("translated", t))
    return pairs


def records_to_chunks(
    records: list[dict[str, Any]],
    strategies: list[ChunkStrategy] | None = None,
) -> list[ChunkDoc]:
    strategies = strategies or ["sentence", "sliding", "semantic", "parent_child"]
    deduper = PassageDeduper()
    docs: list[ChunkDoc] = []

    for rec in records:
        qid = rec.get("query_id")
        for p_idx, (passage_lang, passage) in enumerate(_passages_from_record(rec)):
            if not deduper.keep(f"{passage_lang}:{passage}"):
                continue
            parent_id = f"{rec.get('language')}:{qid}:p{p_idx}:{passage_lang}"

            for strategy in strategies:
                if strategy == "sentence":
                    pieces = sentence_chunks(passage)
                    for i, text in enumerate(pieces):
                        docs.append(
                            ChunkDoc(
                                chunk_id=f"{parent_id}:sentence:{i}",
                                text=text,
                                parent_text=passage,
                                chunk_type="sentence",
                                language=str(rec.get("language") or ""),
                                source_lang=str(rec.get("source_lang") or ""),
                                target_lang=str(rec.get("target_lang") or ""),
                                query_id=qid,
                                query_type=str(rec.get("query_type") or ""),
                                passage_lang=passage_lang,
                                parent_id=parent_id,
                            )
                        )
                elif strategy == "sliding":
                    pieces = sliding_window_chunks(passage, window=3, stride=1)
                    for i, text in enumerate(pieces):
                        docs.append(
                            ChunkDoc(
                                chunk_id=f"{parent_id}:sliding:{i}",
                                text=text,
                                parent_text=passage,
                                chunk_type="sliding",
                                language=str(rec.get("language") or ""),
                                source_lang=str(rec.get("source_lang") or ""),
                                target_lang=str(rec.get("target_lang") or ""),
                                query_id=qid,
                                query_type=str(rec.get("query_type") or ""),
                                passage_lang=passage_lang,
                                parent_id=parent_id,
                            )
                        )
                elif strategy == "semantic":
                    pieces = semantic_chunks(passage)
                    for i, text in enumerate(pieces):
                        docs.append(
                            ChunkDoc(
                                chunk_id=f"{parent_id}:semantic:{i}",
                                text=text,
                                parent_text=passage,
                                chunk_type="semantic",
                                language=str(rec.get("language") or ""),
                                source_lang=str(rec.get("source_lang") or ""),
                                target_lang=str(rec.get("target_lang") or ""),
                                query_id=qid,
                                query_type=str(rec.get("query_type") or ""),
                                passage_lang=passage_lang,
                                parent_id=parent_id,
                            )
                        )
                elif strategy == "parent_child":
                    for pc in parent_child_chunks(parent_id, passage, "sentence"):
                        docs.append(
                            ChunkDoc(
                                chunk_id=f"{pc.child_id}:parent_child",
                                text=pc.child_text,
                                parent_text=pc.parent_text,
                                chunk_type="parent_child",
                                language=str(rec.get("language") or ""),
                                source_lang=str(rec.get("source_lang") or ""),
                                target_lang=str(rec.get("target_lang") or ""),
                                query_id=qid,
                                query_type=str(rec.get("query_type") or ""),
                                passage_lang=passage_lang,
                                parent_id=pc.parent_id,
                            )
                        )
    return docs


def compact_index_chunks(
    records: list[dict[str, Any]],
    max_chunks: int = 20_000,
) -> list[ChunkDoc]:
    """
    One searchable unit per unique passage text, tagged with all matching
    strategy names. Every record is represented before extras fill the cap.
    """
    from ingestion.deduplicate import text_hash

    per_record: list[list[ChunkDoc]] = []
    for rec in records:
        raw = records_to_chunks(
            [rec],
            strategies=["semantic", "parent_child", "sentence", "sliding"],
        )
        seen: dict[str, ChunkDoc] = {}
        types: dict[str, set[str]] = {}
        for doc in raw:
            key = text_hash(doc.text)
            if key not in seen:
                seen[key] = doc
                types[key] = {doc.chunk_type}
            else:
                types[key].add(doc.chunk_type)
        uniq = []
        for key, doc in seen.items():
            doc.chunk_type = "+".join(sorted(types[key]))
            uniq.append(doc)
        # Prefer shorter semantic/parent units first
        uniq.sort(key=lambda d: (len(d.text), d.chunk_type))
        per_record.append(uniq)

    selected: list[ChunkDoc] = []
    # Guarantee coverage: first chunk from every record
    leftovers: list[ChunkDoc] = []
    for group in per_record:
        if not group:
            continue
        selected.append(group[0])
        leftovers.extend(group[1:])
        if len(selected) >= max_chunks:
            return selected[:max_chunks]
    for doc in leftovers:
        if len(selected) >= max_chunks:
            break
        selected.append(doc)
    return selected
