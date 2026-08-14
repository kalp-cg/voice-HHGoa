"""FastAPI entrypoint — voice RAG."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes_health import router as health_router
from backend.api.routes_query import router as query_router
from backend.api.routes_voice import router as voice_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import os

    if os.getenv("SKIP_STARTUP_WARMUP", "").strip() not in {"1", "true", "yes"}:
        try:
            from backend.orchestration.pipeline import run_pipeline

            run_pipeline("What is the capital of India?", mode="fast")
        except Exception:
            pass
    yield


app = FastAPI(
    title="Voice RAG Goa",
    description="Voice → STT → hybrid retrieval → rerank → grounded answer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(voice_router)
app.include_router(query_router)

if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
