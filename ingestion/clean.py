"""Light cleaning for MSMARCO-XI records."""

from __future__ import annotations

import re
from typing import Any

_WS = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    t = text.replace("\u0000", " ").strip()
    t = _WS.sub(" ", t)
    return t


def clean_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    query = clean_text(rec.get("query"))
    eng_query = clean_text(rec.get("eng_query"))
    if not query and not eng_query:
        return None

    eng_passages = [clean_text(p) for p in (rec.get("english_passages") or [])]
    tr_passages = [clean_text(p) for p in (rec.get("translated_passages") or [])]
    eng_passages = [p for p in eng_passages if len(p) >= 40]
    tr_passages = [p for p in tr_passages if len(p) >= 20]

    if not eng_passages and not tr_passages:
        return None

    out = dict(rec)
    out["query"] = query
    out["eng_query"] = eng_query
    out["answer"] = clean_text(rec.get("answer"))
    out["eng_answer"] = clean_text(rec.get("eng_answer"))
    out["english_passages"] = eng_passages
    out["translated_passages"] = tr_passages
    return out
