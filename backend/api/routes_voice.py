"""Voice / STT routes — Milestone 1: single-use Scribe token for browser mic."""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import APIRouter, HTTPException, Request

from backend.core.config import get_settings
from backend.stt.elevenlabs_client import (
    ElevenLabsSTTError,
    create_realtime_scribe_token,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])
_TOKEN_LIMIT = 5
_TOKEN_WINDOW_S = 60.0
_requests: dict[str, deque[float]] = defaultdict(deque)
_requests_lock = Lock()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _allow_token(ip: str) -> bool:
    now = time.monotonic()
    cutoff = now - _TOKEN_WINDOW_S
    with _requests_lock:
        recent = _requests[ip]
        while recent and recent[0] < cutoff:
            recent.popleft()
        if len(recent) >= _TOKEN_LIMIT:
            return False
        recent.append(now)
        return True


@router.get("/scribe-token")
async def scribe_token(request: Request) -> dict[str, str]:
    """Return a single-use token so the browser can connect to Scribe realtime."""
    if not _allow_token(_client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many STT token requests. Try again in one minute.",
        )
    settings = get_settings()
    try:
        token = await create_realtime_scribe_token(settings)
    except ElevenLabsSTTError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"token": token}
