"""Shared retrieval / query schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    chunk_type: str | None = None
    language: str | None = None


class RetrieveHit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: str | None = None
    score: float
    text: str | None = None
    parent_text: str | None = None
    chunk_type: str | None = None
    language: str | None = None
    passage_lang: str | None = None
    query_id: Any = None
    rerank_score: float | None = None


class RetrieveResponse(BaseModel):
    query: str
    hits: list[RetrieveHit]
    latency_ms: dict[str, float]


class QueryRequest(BaseModel):
    query: str
    mode: Literal["fast", "generative"] | None = None
    language: str | None = None


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    query: str
    answer: str
    grounded: bool
    refused: bool
    refusal_reason: str | None = None
    mode: str
    retrieval_mode: str | None = None
    sources: list[RetrieveHit]
    retrieval: dict[str, int]
    confidence: float
    latency_ms: dict[str, float]
    error: str | None = None
