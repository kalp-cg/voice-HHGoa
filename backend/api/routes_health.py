"""Health and readiness."""

from fastapi import APIRouter

from backend.core.config import get_settings
from backend.generation.llm import ollama_available, ollama_has_model
from retrieval.qdrant import get_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    ollama_up = ollama_available(settings.ollama_url)
    model_ok = ollama_has_model(settings.ollama_url, settings.ollama_model) if ollama_up else False
    index_ok = False
    points = 0
    try:
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
        "ollama": ollama_up,
        "ollama_model": settings.ollama_model,
        "ollama_model_ready": model_ok,
        "default_mode": settings.default_answer_mode,
        "milestone": 8,
        "component": "voice-rag",
    }
