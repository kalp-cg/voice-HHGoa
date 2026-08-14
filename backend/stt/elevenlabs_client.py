"""ElevenLabs single-use token helper for Scribe realtime (client-side mic)."""

from __future__ import annotations

import httpx

from backend.core.config import Settings


class ElevenLabsSTTError(Exception):
    """Raised when token creation or STT setup fails."""


async def create_realtime_scribe_token(settings: Settings) -> str:
    """Create a single-use token for Scribe v2 realtime (expires ~15 min)."""
    if not settings.elevenlabs_api_key:
        raise ElevenLabsSTTError(
            "ELEVENLABS_API_KEY is missing. Add it to your .env file."
        )

    url = f"{settings.elevenlabs_api_base.rstrip('/')}/v1/single-use-token/realtime_scribe"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers)

    if response.status_code >= 400:
        detail = response.text
        raise ElevenLabsSTTError(
            f"ElevenLabs token request failed ({response.status_code}): {detail}"
        )

    data = response.json()
    token = data.get("token")
    if not token:
        raise ElevenLabsSTTError(f"Unexpected token response: {data}")
    return token
