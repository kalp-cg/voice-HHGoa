"""Retrieval and end-to-end query routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from backend.core.config import get_settings
from backend.orchestration.pipeline import run_pipeline
from backend.retrieval.hybrid import reciprocal_rank_fusion
from backend.retrieval.reranker import rerank
from backend.retrieval.sparse import sparse_search
from retrieval.schemas import (
    QueryRequest,
    QueryResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
)

router = APIRouter(tags=["retrieve"])


def _to_hits(raw: list[dict]) -> list[RetrieveHit]:
    return [
        RetrieveHit(
            chunk_id=h.get("chunk_id"),
            score=float(h.get("score") or 0.0),
            text=h.get("text"),
            parent_text=h.get("parent_text"),
            chunk_type=h.get("chunk_type"),
            language=h.get("language"),
            passage_lang=h.get("passage_lang"),
            query_id=h.get("query_id"),
            rerank_score=h.get("rerank_score"),
        )
        for h in raw
    ]


@router.post("/api/retrieve/dense", response_model=RetrieveResponse)
async def retrieve_dense(body: RetrieveRequest) -> RetrieveResponse:
    settings = get_settings()
    if (settings.retrieval_mode or "").strip().lower() == "sparse":
        raise HTTPException(
            status_code=501,
            detail="Dense retrieval disabled in sparse deploy mode",
        )
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    from backend.retrieval.dense import dense_retrieve

    t0 = time.perf_counter()
    try:
        hits_raw, t_embed = dense_retrieve(
            query,
            top_k=body.top_k,
            qdrant_path=settings.qdrant_path,
            qdrant_url=settings.qdrant_url,
            chunk_type=body.chunk_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Dense search failed: {exc}") from exc
    total = (time.perf_counter() - t0) * 1000
    return RetrieveResponse(
        query=query,
        hits=_to_hits(hits_raw),
        latency_ms={
            "embedding": round(t_embed, 2),
            "retrieval": round(max(0.0, total - t_embed), 2),
            "total": round(total, 2),
        },
    )


@router.post("/api/retrieve/sparse", response_model=RetrieveResponse)
async def retrieve_sparse(body: RetrieveRequest) -> RetrieveResponse:
    settings = get_settings()
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    t0 = time.perf_counter()
    try:
        hits_raw = sparse_search(query, limit=body.top_k, path=settings.qdrant_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"BM25 search failed: {exc}") from exc
    t_ms = (time.perf_counter() - t0) * 1000
    if body.chunk_type:
        hits_raw = [h for h in hits_raw if h.get("chunk_type") == body.chunk_type]
    return RetrieveResponse(
        query=query,
        hits=_to_hits(hits_raw[: body.top_k]),
        latency_ms={"bm25": round(t_ms, 2), "total": round(t_ms, 2)},
    )


@router.post("/api/retrieve/hybrid", response_model=RetrieveResponse)
async def retrieve_hybrid(body: RetrieveRequest) -> RetrieveResponse:
    settings = get_settings()
    if (settings.retrieval_mode or "").strip().lower() == "sparse":
        raise HTTPException(
            status_code=501,
            detail="Hybrid retrieval disabled in sparse deploy mode; use /api/retrieve/sparse",
        )
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    candidate_k = max(body.top_k * 2, 20)

    from backend.retrieval.dense import dense_retrieve

    t0 = time.perf_counter()
    dense_hits, t_embed = dense_retrieve(
        query,
        top_k=candidate_k,
        qdrant_path=settings.qdrant_path,
        qdrant_url=settings.qdrant_url,
        chunk_type=body.chunk_type,
    )
    t_dense = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    sparse_hits = sparse_search(query, limit=candidate_k, path=settings.qdrant_path)
    if body.chunk_type:
        sparse_hits = [h for h in sparse_hits if h.get("chunk_type") == body.chunk_type]
    t_sparse = (time.perf_counter() - t1) * 1000

    t2 = time.perf_counter()
    fused = reciprocal_rank_fusion([dense_hits, sparse_hits], k=60, limit=candidate_k)
    selected = rerank(query, fused, top_k=body.top_k, model_name=settings.reranker_model)
    t_fuse = (time.perf_counter() - t2) * 1000
    total = t_dense + t_sparse + t_fuse

    return RetrieveResponse(
        query=query,
        hits=_to_hits(selected),
        latency_ms={
            "embedding": round(t_embed, 2),
            "dense": round(t_dense, 2),
            "bm25": round(t_sparse, 2),
            "fusion_rerank": round(t_fuse, 2),
            "total": round(total, 2),
        },
    )


@router.post("/api/query", response_model=QueryResponse)
async def query_rag(body: QueryRequest) -> QueryResponse:
    result = run_pipeline(body.query, mode=body.mode)
    return QueryResponse(**result)


@router.post("/api/query/fast", response_model=QueryResponse)
async def query_fast(body: QueryRequest) -> QueryResponse:
    result = run_pipeline(body.query, mode="fast")
    return QueryResponse(**result)
