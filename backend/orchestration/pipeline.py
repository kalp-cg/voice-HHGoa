"""Structured RAG orchestration harness."""

from __future__ import annotations

import uuid
import time
from typing import Any, Literal

from backend.core.config import Settings, get_settings
from backend.core.languages import resolve_languages
from backend.core.telemetry import StageTimer
from backend.generation.extractive import extractive_answer
from backend.generation.llm import OllamaError, generate_answer, ollama_has_model
from backend.generation.prompts import REFUSAL
from backend.guardrails.grounding import verify_grounding
from backend.guardrails.relevance import should_refuse
from backend.guardrails.safety import UNSAFE_MESSAGE, is_unsafe
from backend.retrieval.hybrid import reciprocal_rank_fusion
from backend.retrieval.reranker import rerank
from backend.retrieval.sparse import sparse_search

AnswerMode = Literal["fast", "generative"]


def _passages(hits: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for h in hits:
        text = (h.get("parent_text") or h.get("text") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text[:1200])
    return out


def run_pipeline(
    query: str,
    *,
    mode: AnswerMode | None = None,
    settings: Settings | None = None,
    language: str | None = None,
    language_hint: str | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    mode = mode or settings.default_answer_mode  # type: ignore[assignment]
    if mode not in ("fast", "generative"):
        mode = "fast"

    timer = StageTimer()
    request_id = uuid.uuid4().hex[:12]
    query = (query or "").strip()
    retrieval_mode = (settings.retrieval_mode or "hybrid").strip().lower()
    if retrieval_mode not in ("hybrid", "sparse"):
        retrieval_mode = "hybrid"
    # Nothing is selected by hand in the normal flow: the query's own script,
    # optionally narrowed by the language speech recognition reported, decides.
    languages = resolve_languages(query, forced=language, hint=language_hint)

    envelope: dict[str, Any] = {
        "request_id": request_id,
        "query": query,
        "answer": "",
        "grounded": False,
        "refused": False,
        "refusal_reason": None,
        "mode": mode,
        "retrieval_mode": retrieval_mode,
        "query_language": ",".join(sorted(languages)),
        "sources": [],
        "retrieval": {"candidates": 0, "selected": 0},
        "confidence": 0.0,
        "latency_ms": {},
        "error": None,
    }

    if not query:
        envelope["refused"] = True
        envelope["refusal_reason"] = "empty_query"
        envelope["answer"] = REFUSAL
        envelope["latency_ms"] = timer.as_dict()
        return envelope

    with timer.track("guardrails"):
        if is_unsafe(query):
            envelope["refused"] = True
            envelope["refusal_reason"] = "unsafe"
            envelope["answer"] = UNSAFE_MESSAGE
            envelope["latency_ms"] = timer.as_dict()
            return envelope

    dense_hits: list[dict[str, Any]] = []
    if retrieval_mode == "hybrid":
        try:
            from backend.retrieval.dense import dense_retrieve

            t_dense0 = time.perf_counter()
            dense_hits, embed_ms = dense_retrieve(
                query,
                top_k=settings.hybrid_candidates,
                qdrant_path=settings.qdrant_path,
                qdrant_url=settings.qdrant_url,
            )
            timer.add("embedding", embed_ms)
            timer.add(
                "dense",
                max(0.0, (time.perf_counter() - t_dense0) * 1000 - embed_ms),
            )
        except Exception as exc:  # noqa: BLE001
            envelope["error"] = f"dense_failed:{exc}"
            envelope["refused"] = True
            envelope["answer"] = REFUSAL
            envelope["latency_ms"] = timer.as_dict()
            return envelope
    else:
        timer.add("embedding", 0.0)
        timer.add("dense", 0.0)

    with timer.track("bm25"):
        try:
            sparse_hits = sparse_search(
                query,
                limit=settings.hybrid_candidates,
                path=settings.qdrant_path,
                languages=languages,
            )
        except Exception as exc:  # noqa: BLE001
            sparse_hits = []
            envelope["error"] = f"bm25_failed:{exc}"

    with timer.track("fusion"):
        if retrieval_mode == "sparse":
            fused = sparse_hits[: settings.hybrid_candidates]
        else:
            fused = reciprocal_rank_fusion(
                [dense_hits, sparse_hits],
                k=60,
                limit=settings.hybrid_candidates,
            )

    with timer.track("rerank"):
        selected = rerank(
            query,
            fused,
            top_k=settings.rerank_top_k,
            model_name=settings.reranker_model,
        )

    envelope["retrieval"] = {
        "candidates": len(fused),
        "selected": len(selected),
    }

    with timer.track("guardrails"):
        refuse, conf, msg = should_refuse(selected, settings.relevance_threshold, query)
        envelope["confidence"] = round(conf, 4)
        if refuse:
            envelope["refused"] = True
            envelope["refusal_reason"] = "low_confidence"
            envelope["answer"] = msg
            envelope["sources"] = selected[:3]
            envelope["latency_ms"] = timer.as_dict()
            return envelope

    passages = _passages(selected)
    used_mode = mode
    fallback_note = None

    with timer.track("generation"):
        if mode == "generative":
            if ollama_has_model(settings.ollama_url, settings.ollama_model):
                try:
                    answer = generate_answer(
                        query,
                        passages,
                        base_url=settings.ollama_url,
                        model=settings.ollama_model,
                        timeout_s=settings.ollama_timeout_s,
                        max_tokens=settings.llm_max_tokens,
                    )
                except OllamaError as exc:
                    answer = extractive_answer(query, selected)
                    used_mode = "fast"
                    fallback_note = f"ollama_error:{exc}"
            else:
                answer = extractive_answer(query, selected)
                used_mode = "fast"
                fallback_note = "ollama_unavailable"
        else:
            answer = extractive_answer(query, selected)

    with timer.track("grounding"):
        grounded, overlap, answer = verify_grounding(
            answer, selected, settings.grounding_overlap
        )

    envelope["mode"] = used_mode
    envelope["answer"] = answer
    envelope["grounded"] = grounded
    envelope["sources"] = selected
    envelope["confidence"] = round(max(envelope["confidence"], overlap), 4)
    if not grounded:
        envelope["refused"] = True
        envelope["refusal_reason"] = "ungrounded"
    if fallback_note:
        envelope["error"] = fallback_note
    envelope["latency_ms"] = timer.as_dict()
    return envelope
