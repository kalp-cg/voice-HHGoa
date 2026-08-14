"""BM25 sparse retrieval over indexed chunk texts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"[\w\u0900-\u0D7F\u0600-\u06FF]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "") if t.strip()]


@dataclass
class SparseDoc:
    chunk_id: str
    text: str
    parent_text: str
    chunk_type: str
    language: str
    passage_lang: str
    query_id: Any


class BM25Index:
    def __init__(self, docs: list[SparseDoc]) -> None:
        self.docs = docs
        self._tokens = [tokenize(d.text) for d in docs]
        self._bm25 = BM25Okapi(self._tokens) if docs else None

    def search(
        self,
        query: str,
        limit: int = 20,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._bm25 or not self.docs:
            return []
        q = tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        lang = (language or "").strip().lower()
        allowed_ids = [
            i
            for i, d in enumerate(self.docs)
            if not lang or (d.language or "").strip().lower() == lang
        ]
        if not allowed_ids:
            return []
        allowed = np.array(allowed_ids, dtype=int)
        sub = scores[allowed]
        candidate_count = min(limit, sub.size)
        if candidate_count == sub.size:
            order = np.argsort(sub)[::-1]
        else:
            top = np.argpartition(sub, -candidate_count)[-candidate_count:]
            order = top[np.argsort(sub[top])[::-1]]
        out: list[dict[str, Any]] = []
        for pos in order:
            i = int(allowed[int(pos)])
            if scores[i] <= 0:
                continue
            d = self.docs[i]
            out.append(
                {
                    "chunk_id": d.chunk_id,
                    "score": float(scores[i]),
                    "text": d.text,
                    "parent_text": d.parent_text,
                    "chunk_type": d.chunk_type,
                    "language": d.language,
                    "passage_lang": d.passage_lang,
                    "query_id": d.query_id,
                }
            )
        return out


def _row_to_doc(payload: dict[str, Any], fallback_id: str) -> SparseDoc | None:
    text = payload.get("text") or ""
    if not str(text).strip():
        return None
    return SparseDoc(
        chunk_id=str(payload.get("chunk_id") or fallback_id),
        text=str(text),
        parent_text=str(payload.get("parent_text") or ""),
        chunk_type=str(payload.get("chunk_type") or ""),
        language=str(payload.get("language") or ""),
        passage_lang=str(payload.get("passage_lang") or ""),
        query_id=payload.get("query_id"),
    )


def _load_docs_from_jsonl(path: Path) -> list[SparseDoc]:
    docs: list[SparseDoc] = []
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            row = json.loads(line)
            doc = _row_to_doc(row, fallback_id=f"jsonl:{i}")
            if doc:
                docs.append(doc)
    return docs


def _load_docs_from_qdrant(
    path: str = "qdrant_storage/local",
    collection: str = "msmarco_xi_mini",
) -> list[SparseDoc]:
    from retrieval.qdrant import COLLECTION, get_client

    client = get_client(url="", path=path)
    docs: list[SparseDoc] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection or COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            payload = p.payload or {}
            doc = _row_to_doc(payload, fallback_id=str(p.id))
            if doc:
                docs.append(doc)
        if offset is None:
            break
    return docs


def _resolve_docs(path: str = "qdrant_storage/local") -> list[SparseDoc]:
    base = Path(path)
    jsonl = base / "chunks.jsonl"
    if jsonl.is_file():
        return _load_docs_from_jsonl(jsonl)
    return _load_docs_from_qdrant(path=path)


@lru_cache(maxsize=1)
def get_bm25_index(path: str = "qdrant_storage/local") -> BM25Index:
    docs = _resolve_docs(path)
    return BM25Index(docs)


def sparse_search(
    query: str,
    limit: int = 20,
    path: str = "qdrant_storage/local",
    language: str | None = None,
) -> list[dict[str, Any]]:
    return get_bm25_index(path).search(query, limit=limit, language=language)
