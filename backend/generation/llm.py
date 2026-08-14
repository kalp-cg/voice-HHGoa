"""Local Ollama client for grounded generation."""

from __future__ import annotations

from typing import Any

import httpx

from backend.generation.prompts import REFUSAL, SYSTEM_GROUNDED, build_user_prompt


class OllamaError(Exception):
    pass


def ollama_available(base_url: str, timeout_s: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout_s)
        return r.status_code == 200
    except Exception:
        return False


def ollama_has_model(base_url: str, model: str, timeout_s: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout_s)
        if r.status_code != 200:
            return False
        names = [m.get("name") for m in r.json().get("models", [])]
        return model in names or any(str(n).startswith(model) for n in names)
    except Exception:
        return False


def generate_answer(
    question: str,
    passages: list[str],
    *,
    base_url: str,
    model: str,
    timeout_s: float = 25.0,
    max_tokens: int = 96,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_GROUNDED},
            {"role": "user", "content": build_user_prompt(question, passages)},
        ],
        "options": {
            "temperature": 0.0,
            "num_predict": max_tokens,
        },
    }
    try:
        r = httpx.post(
            f"{base_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=timeout_s,
        )
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama request failed: {exc}") from exc
    if r.status_code >= 400:
        raise OllamaError(f"Ollama HTTP {r.status_code}: {r.text[:240]}")
    data = r.json()
    text = (data.get("message") or {}).get("content") or ""
    text = text.strip()
    return text or REFUSAL
