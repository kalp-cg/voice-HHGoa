"""Health and readiness."""

from pathlib import Path

from fastapi import APIRouter

from backend.core.config import get_settings
from backend.generation.llm import ollama_available, ollama_has_model

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    ollama_up = ollama_available(settings.ollama_url)
    model_ok = (
        ollama_has_model(settings.ollama_url, settings.ollama_model) if ollama_up else False
    )
    index_ok = False
    points = 0
    languages: list[str] = []
    retrieval_mode = (settings.retrieval_mode or "hybrid").strip().lower()

    chunks_path = Path(settings.qdrant_path) / "chunks.jsonl"
    if chunks_path.is_file():
        index_ok = True
        try:
            import json

            langs: set[str] = set()
            with chunks_path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    points += 1
                    lang = (json.loads(line).get("language") or "").strip()
                    if lang:
                        langs.add(lang)
            languages = sorted(langs)
        except OSError:
            points = 0
    elif retrieval_mode != "sparse":
        try:
            from retrieval.qdrant import get_client

            client = get_client(url=settings.qdrant_url, path=settings.qdrant_path)
            index_ok = client.collection_exists(settings.qdrant_collection)
            if index_ok:
                info = client.get_collection(settings.qdrant_collection)
                points = int(getattr(info, "points_count", 0) or 0)
        except Exception:
            index_ok = False

    return {
        "status": "ok" if index_ok else "degraded",
        "elevenlabs_configured": bool(settings.elevenlabs_api_key),
        "index_ready": index_ok,
        "index_points": points,
        "languages": languages,
        "retrieval_mode": retrieval_mode,
        "ollama": ollama_up,
        "ollama_model": settings.ollama_model,
        "ollama_model_ready": model_ok,
        "default_mode": settings.default_answer_mode,
        "milestone": 21,
        "component": "voice-rag",
    }
