"""Deduplicate passages by normalized text hash."""

from __future__ import annotations

import hashlib
from typing import Iterable


def _norm_key(text: str) -> str:
    return " ".join(text.lower().split())


def text_hash(text: str) -> str:
    return hashlib.sha1(_norm_key(text).encode("utf-8")).hexdigest()


class PassageDeduper:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def keep(self, text: str) -> bool:
        h = text_hash(text)
        if h in self._seen:
            return False
        self._seen.add(h)
        return True

    @property
    def size(self) -> int:
        return len(self._seen)


def unique_texts(texts: Iterable[str]) -> list[str]:
    deduper = PassageDeduper()
    out: list[str] = []
    for t in texts:
        if t and deduper.keep(t):
            out.append(t)
    return out
