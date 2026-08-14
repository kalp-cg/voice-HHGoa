"""Deduplicate retrieval hits by parent passage / normalized text."""

from __future__ import annotations

import hashlib
from typing import Any


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def hit_key(hit: dict[str, Any]) -> str:
    parent = _norm(str(hit.get("parent_text") or hit.get("text") or ""))
    if parent:
        return hashlib.sha1(parent.encode("utf-8")).hexdigest()[:16]
    return str(hit.get("chunk_id") or "")


def dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for hit in hits:
        key = hit_key(hit)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out
