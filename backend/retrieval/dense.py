"""Dense retrieval helpers (thin wrappers used by the API/orchestration)."""

from __future__ import annotations

from typing import Any

from ingestion.embed import embed_query
from retrieval.qdrant import dense_search, get_client


def dense_retrieve(
    query: str,
    top_k: int = 20,
    qdrant_path: str = "qdrant_storage/local",
    qdrant_url: str = "",
    chunk_type: str | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Returns (hits, embed_ms)."""
    import time

    t0 = time.perf_counter()
    vector = embed_query(query)
    embed_ms = (time.perf_counter() - t0) * 1000
    client = get_client(url=qdrant_url, path=qdrant_path)
    hits = dense_search(client, vector, limit=top_k, chunk_type=chunk_type)
    return hits, embed_ms
