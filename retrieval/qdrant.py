"""Qdrant helpers: embedded local store + dense search (no Docker required)."""

from __future__ import annotations

import atexit
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

COLLECTION = "msmarco_xi_mini"
VECTOR_SIZE = 384
DEFAULT_PATH = Path("qdrant_storage/local")


def point_id(chunk_id: str) -> int:
    h = hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()
    return int(h[:16], 16) % (2**63 - 1)


@lru_cache(maxsize=1)
def get_client(url: str = "", path: str = "") -> QdrantClient:
    """Prefer embedded path store; optional HTTP URL if set and path empty."""
    if url and url.startswith("http") and not path:
        client = QdrantClient(url=url, timeout=60)
    else:
        store = Path(path) if path else DEFAULT_PATH
        store.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(store))
    atexit.register(client.close)
    return client


def ensure_collection(
    client: QdrantClient,
    name: str = COLLECTION,
    vector_size: int = VECTOR_SIZE,
    recreate: bool = False,
) -> None:
    exists = client.collection_exists(name)
    if exists and recreate:
        client.delete_collection(name)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(
                size=vector_size,
                distance=qm.Distance.COSINE,
            ),
        )


def upsert_chunks(
    client: QdrantClient,
    texts: list[str],
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
    collection: str = COLLECTION,
    batch_size: int = 64,
) -> int:
    assert len(texts) == len(vectors) == len(payloads)
    total = 0
    for start in range(0, len(texts), batch_size):
        end = start + batch_size
        points = []
        for text, vec, payload in zip(
            texts[start:end], vectors[start:end], payloads[start:end], strict=True
        ):
            body = dict(payload)
            body["text"] = text
            points.append(
                qm.PointStruct(
                    id=point_id(str(payload["chunk_id"])),
                    vector=vec,
                    payload=body,
                )
            )
        client.upsert(collection_name=collection, points=points)
        total += len(points)
    return total


def dense_search(
    client: QdrantClient,
    query_vector: list[float],
    limit: int = 10,
    collection: str = COLLECTION,
    chunk_type: str | None = None,
) -> list[dict[str, Any]]:
    query_filter = None
    if chunk_type:
        query_filter = qm.Filter(
            must=[
                qm.FieldCondition(
                    key="chunk_type",
                    match=qm.MatchValue(value=chunk_type),
                )
            ]
        )

    # qdrant-client >=1.12 prefers query_points
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        hits = res.points
    else:
        hits = client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    out: list[dict[str, Any]] = []
    for h in hits:
        payload = h.payload or {}
        out.append(
            {
                "id": h.id,
                "score": h.score,
                "text": payload.get("text"),
                "parent_text": payload.get("parent_text"),
                "chunk_type": payload.get("chunk_type"),
                "language": payload.get("language"),
                "query_id": payload.get("query_id"),
                "chunk_id": payload.get("chunk_id"),
                "passage_lang": payload.get("passage_lang"),
            }
        )
    return out
