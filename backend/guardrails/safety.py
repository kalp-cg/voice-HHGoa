"""Input safety / abuse filter."""

from __future__ import annotations

import re

UNSAFE_PATTERNS = [
    r"\bhow to make (a )?(bomb|explosive|napalm)\b",
    r"\bkill (myself|himself|herself)\b",
    r"\bsuicide\b",
    r"\bchild (porn|sexual)\b",
    r"\bhack (into|someone)\b",
    r"\bcredit card (dump|cvv)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in UNSAFE_PATTERNS]

UNSAFE_MESSAGE = "I cannot help with that request."


def is_unsafe(query: str) -> bool:
    q = query or ""
    return any(p.search(q) for p in _COMPILED)
