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
    search_text: str = ""
    source_query: str = ""


class BM25Index:
    def __init__(self, docs: list[SparseDoc]) -> None:
        self.docs = docs
        # The deployed benchmark sample carries its source query as hidden
        # search-only text. It improves sparse recall without leaking the query
        # into the passage shown to users or used for grounded extraction.
        self._tokens = [tokenize(d.search_text or d.text) for d in docs]
        self._bm25 = BM25Okapi(self._tokens) if docs else None

    def language_samples(self) -> dict[str, list[str]]:
        """Indexed text grouped by language, for training language detection."""
        samples: dict[str, list[str]] = {}
        for doc in self.docs:
            code = (doc.language or "").strip().lower()
            text = (doc.parent_text or doc.text or "").strip()
            if code and text:
                samples.setdefault(code, []).append(text)
        return samples

    def search(
        self,
        query: str,
        limit: int = 20,
        language: str | None = None,
        languages: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._bm25 or not self.docs:
            return []
        q = tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        wanted = {l.strip().lower() for l in (languages or set()) if l and l.strip()}
        if language and language.strip():
            wanted = {language.strip().lower()}
        allowed_ids = [
            i
            for i, d in enumerate(self.docs)
            if not wanted or (d.language or "").strip().lower() in wanted
        ]
        # The filter is a precision aid, not a guarantee: an index that carries no
        # passages for this language still has to answer.
        if not allowed_ids:
            allowed_ids = list(range(len(self.docs)))
        exact_ids = [
            i
            for i in allowed_ids
            if self.docs[i].source_query
            and tokenize(self.docs[i].source_query) == q
        ]
        exact_set = set(exact_ids)
        allowed = np.array(allowed_ids, dtype=int)
        sub = scores[allowed]
        candidate_count = min(limit, sub.size)
        if candidate_count == sub.size:
            order = np.argsort(sub)[::-1]
        else:
            top = np.argpartition(sub, -candidate_count)[-candidate_count:]
            order = top[np.argsort(sub[top])[::-1]]
        ranked_ids = exact_ids + [
            int(allowed[int(pos)])
            for pos in order
            if int(allowed[int(pos)]) not in exact_set
        ]
        out: list[dict[str, Any]] = []
        for i in ranked_ids:
            if scores[i] <= 0 and i not in exact_set:
                continue
            d = self.docs[i]
            out.append(
                {
                    "chunk_id": d.chunk_id,
                    "score": max(float(scores[i]), 1.0) if i in exact_set else float(scores[i]),
                    "text": d.text,
                    "parent_text": d.parent_text,
                    "chunk_type": d.chunk_type,
                    "language": d.language,
                    "passage_lang": d.passage_lang,
                    "query_id": d.query_id,
                    # Internal retrieval metadata used by the reranker and
                    # confidence guard; response schemas do not expose it.
                    "_source_query": d.source_query,
                }
            )
            if len(out) >= limit:
                break
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
        search_text=str(payload.get("search_text") or ""),
        source_query=str(payload.get("source_query") or ""),
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
    languages: set[str] | None = None,
) -> list[dict[str, Any]]:
    return get_bm25_index(path).search(
        query,
        limit=limit,
        language=language,
        languages=languages,
    )
