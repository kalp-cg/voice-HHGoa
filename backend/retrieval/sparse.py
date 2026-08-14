"""BM25 sparse retrieval over indexed chunk texts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from retrieval.qdrant import COLLECTION, get_client

_TOKEN = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)


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

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._bm25 or not self.docs:
            return []
        q = tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        candidate_count = min(limit, len(scores))
        if candidate_count == len(scores):
            ranked = np.argsort(scores)[::-1]
        else:
            candidate_ids = np.argpartition(scores, -candidate_count)[-candidate_count:]
            ranked = candidate_ids[np.argsort(scores[candidate_ids])[::-1]]
        out: list[dict[str, Any]] = []
        for i in ranked:
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


def _load_docs_from_qdrant(
    path: str = "qdrant_storage/local",
    collection: str = COLLECTION,
) -> list[SparseDoc]:
    client = get_client(url="", path=path)
    docs: list[SparseDoc] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            payload = p.payload or {}
            text = payload.get("text") or ""
            if not text.strip():
                continue
            docs.append(
                SparseDoc(
                    chunk_id=str(payload.get("chunk_id") or p.id),
                    text=text,
                    parent_text=str(payload.get("parent_text") or ""),
                    chunk_type=str(payload.get("chunk_type") or ""),
                    language=str(payload.get("language") or ""),
                    passage_lang=str(payload.get("passage_lang") or ""),
                    query_id=payload.get("query_id"),
                )
            )
        if offset is None:
            break
    return docs


@lru_cache(maxsize=1)
def get_bm25_index(path: str = "qdrant_storage/local") -> BM25Index:
    docs = _load_docs_from_qdrant(path=path)
    return BM25Index(docs)


def sparse_search(
    query: str,
    limit: int = 20,
    path: str = "qdrant_storage/local",
) -> list[dict[str, Any]]:
    return get_bm25_index(path).search(query, limit=limit)
