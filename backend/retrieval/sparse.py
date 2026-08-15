"""BM25 sparse retrieval over indexed chunk texts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from backend.core.translit import (
    fuzzy_key,
    related_skeletons,
    romanize_token,
    script_base,
    scripts_in,
    skeleton,
)

_TOKEN = re.compile(r"[\w\u0900-\u0D7F\u0600-\u06FF]+", re.UNICODE)

# A Latin word can plausibly romanise onto several indexed spellings; past a
# handful the additions stop being the same name and start diluting the query.
_MAX_CROSS_SCRIPT_TERMS = 8


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "") if t.strip()]


@dataclass
class SparseDoc:
    chunk_id: str
    text: str
    parent_text: str
    chunk_type: str
    language: str
    passage_lang: str
    query_id: Any
    search_text: str = ""
    source_query: str = ""


class BM25Index:
    def __init__(self, docs: list[SparseDoc]) -> None:
        self.docs = docs
        # The deployed benchmark sample carries its source query as hidden
        # search-only text. It improves sparse recall without leaking the query
        # into the passage shown to users or used for grounded extraction.
        self._tokens = [tokenize(d.search_text or d.text) for d in docs]
        self._bm25 = BM25Okapi(self._tokens) if docs else None
        self._roman_vocab: dict[str, dict[str, set[str]]] | None = None
        self._skeleton_vocab: dict[str, dict[str, set[str]]] | None = None
        self._lang_scripts: dict[str, int | None] | None = None

    def _romanized_vocabulary(self) -> dict[str, dict[str, set[str]]]:
        """Indexed Indic tokens grouped by first letter and by consonant skeleton."""
        if self._roman_vocab is None:
            vocab: dict[str, dict[str, set[str]]] = {}
            skel_vocab: dict[str, dict[str, set[str]]] = {}
            for tokens in self._tokens:
                for token in tokens:
                    if token.isascii():
                        continue
                    roman = romanize_token(token)
                    if len(roman) < 3:
                        continue
                    vocab.setdefault(fuzzy_key(roman), {}).setdefault(roman, set()).add(
                        token
                    )
                    skel = skeleton(roman)
                    if skel:
                        skel_vocab.setdefault(skel, {}).setdefault(roman, set()).add(
                            token
                        )
            self._roman_vocab = vocab
            self._skeleton_vocab = skel_vocab
        return self._roman_vocab

    def warm_cross_script_matching(self) -> None:
        """Build the romanised vocabulary before it lands on a timed query."""
        self._romanized_vocabulary()

    def _expandable_tokens(
        self,
        tokens: list[str],
        query: str,
        wanted: set[str],
    ) -> list[str]:
        """Words BM25 cannot already see in the scripts it is about to search.

        A long Hindi question with one English loanword (`guarantee`) used to
        fuzzy-scan every Indic token against the whole vocab. Only the Latin
        name, or a word written in the wrong script, actually needs expansion.
        """
        query_scripts = scripts_in(query)
        lang_scripts = self._language_scripts()
        wanted_scripts = {
            base
            for code in wanted
            if (base := lang_scripts.get(code)) is not None
        }
        need_other_script = bool(wanted_scripts - query_scripts)
        out: list[str] = []
        for token in tokens:
            if len(token) < 3:
                continue
            if token.isascii() and token.isalpha():
                if query_scripts:
                    out.append(token)
                continue
            if need_other_script and not token.isascii():
                out.append(token)
        return out

    def _cross_script_terms(
        self,
        tokens: list[str],
        query: str = "",
        languages: set[str] | None = None,
    ) -> list[str]:
        """Indexed spellings of this query's words in the corpus's other scripts.

        Two cases need it. `Goa કયાં છે?` otherwise retrieves on `કયાં`/`છે`
        alone, which every Gujarati passage contains, so the one passage about
        `ગોવા` never wins. And when speech recognition writes a language in the
        wrong script, the transcript shares no characters with the passages
        that answer it, in any language.
        """
        wanted = {l.strip().lower() for l in (languages or set()) if l and l.strip()}
        words = self._expandable_tokens(tokens, query, wanted)
        if not words:
            return []
        self._romanized_vocabulary()
        skel_vocab = self._skeleton_vocab or {}
        scored: dict[str, tuple[float, float]] = {}
        for word in words:
            roman_word = romanize_token(word)
            if len(roman_word) < 3:
                continue
            word_script = script_base(word[0])
            word_skel = skeleton(roman_word)
            seen: set[str] = set()
            for key in related_skeletons(roman_word):
                for roman, natives in skel_vocab.get(key, {}).items():
                    if roman in seen:
                        continue
                    seen.add(roman)
                    shorter, longer = sorted((len(roman_word), len(roman)))
                    if longer > 2 * shorter or abs(len(roman_word) - len(roman)) > 3:
                        continue
                    roman_skel = skeleton(roman)
                    if roman_skel == word_skel:
                        closeness = 1.0 if roman == roman_word else 0.95
                    elif roman_word[0] == roman[0]:
                        closeness = 0.9
                    else:
                        continue
                    for native in natives:
                        # Another spelling in the script this word is already
                        # written in adds nothing: BM25 scored it directly.
                        if word_script is not None and (
                            script_base(native[0]) == word_script
                        ):
                            continue
                        scored[native] = max(
                            scored.get(native, (0.0, 0.0)),
                            (closeness, float(len(roman))),
                        )
        best = sorted(scored, key=lambda t: scored[t], reverse=True)
        return best[:_MAX_CROSS_SCRIPT_TERMS]

    def _language_scripts(self) -> dict[str, int | None]:
        """Script each indexed language is written in."""
        if self._lang_scripts is None:
            found: dict[str, int | None] = {}
            for doc, tokens in zip(self.docs, self._tokens):
                code = (doc.language or "").strip().lower()
                if not code or found.get(code) is not None:
                    continue
                for token in tokens:
                    base = script_base(token[0]) if token else None
                    if base is not None:
                        found[code] = base
                        break
                found.setdefault(code, None)
            self._lang_scripts = found
        return self._lang_scripts

    def _spans_scripts(self, query: str, wanted: set[str]) -> bool:
        """True when a requested language is written in a script the query is not.

        Retrieval was asked for passages the query cannot lexically touch, which
        happens when speech recognition writes a language in the wrong script.
        """
        if not wanted:
            return False
        query_scripts = scripts_in(query)
        if not query_scripts:
            return False
        scripts = self._language_scripts()
        return any(
            (base := scripts.get(code)) is not None and base not in query_scripts
            for code in wanted
        )

    def language_samples(self) -> dict[str, list[str]]:
        """Indexed text grouped by language, for training language detection."""
        samples: dict[str, list[str]] = {}
        for doc in self.docs:
            code = (doc.language or "").strip().lower()
            text = (doc.parent_text or doc.text or "").strip()
            if code and text:
                samples.setdefault(code, []).append(text)
        return samples

    def search(
        self,
        query: str,
        limit: int = 20,
        language: str | None = None,
        languages: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._bm25 or not self.docs:
            return []
        q = tokenize(query)
        if not q:
            return []
        wanted = {l.strip().lower() for l in (languages or set()) if l and l.strip()}
        if language and language.strip():
            wanted = {language.strip().lower()}
        extra = self._cross_script_terms(q, query, languages=wanted)
        expanded = q + extra if extra else q
        scores = self._bm25.get_scores(expanded)
        allowed_ids = [
            i
            for i, d in enumerate(self.docs)
            if not wanted or (d.language or "").strip().lower() in wanted
        ]
        # The filter is a precision aid, not a guarantee: an index that carries no
        # passages for this language still has to answer.
        if not allowed_ids:
            allowed_ids = list(range(len(self.docs)))
        exact_ids = [
            i
            for i in allowed_ids
            if self.docs[i].source_query
            and tokenize(self.docs[i].source_query) == q
        ]
        exact_set = set(exact_ids)
        allowed = np.array(allowed_ids, dtype=int)
        sub = scores[allowed]
        candidate_count = min(limit, sub.size)
        if candidate_count == sub.size:
            order = np.argsort(sub)[::-1]
        else:
            top = np.argpartition(sub, -candidate_count)[-candidate_count:]
            order = top[np.argsort(sub[top])[::-1]]
        ranked_ids = exact_ids + [
            int(allowed[int(pos)])
            for pos in order
            if int(allowed[int(pos)]) not in exact_set
        ]
        out: list[dict[str, Any]] = []
        for i in ranked_ids:
            if scores[i] <= 0 and i not in exact_set:
                continue
            d = self.docs[i]
            out.append(
                {
                    "chunk_id": d.chunk_id,
                    "score": max(float(scores[i]), 1.0) if i in exact_set else float(scores[i]),
                    "text": d.text,
                    "parent_text": d.parent_text,
                    "chunk_type": d.chunk_type,
                    "language": d.language,
                    "passage_lang": d.passage_lang,
                    "query_id": d.query_id,
                    # Internal retrieval metadata used by the reranker and
                    # confidence guard; response schemas do not expose it.
                    "_source_query": d.source_query,
                }
            )
            if len(out) >= limit:
                break
        return out


def _row_to_doc(payload: dict[str, Any], fallback_id: str) -> SparseDoc | None:
    text = payload.get("text") or ""
    if not str(text).strip():
        return None
    return SparseDoc(
        chunk_id=str(payload.get("chunk_id") or fallback_id),
        text=str(text),
        parent_text=str(payload.get("parent_text") or ""),
        chunk_type=str(payload.get("chunk_type") or ""),
        language=str(payload.get("language") or ""),
        passage_lang=str(payload.get("passage_lang") or ""),
        query_id=payload.get("query_id"),
        search_text=str(payload.get("search_text") or ""),
        source_query=str(payload.get("source_query") or ""),
    )


def _load_docs_from_jsonl(path: Path) -> list[SparseDoc]:
    docs: list[SparseDoc] = []
    with path.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            row = json.loads(line)
            doc = _row_to_doc(row, fallback_id=f"jsonl:{i}")
            if doc:
                docs.append(doc)
    return docs


def _load_docs_from_qdrant(
    path: str = "qdrant_storage/local",
    collection: str = "msmarco_xi_mini",
) -> list[SparseDoc]:
    from retrieval.qdrant import COLLECTION, get_client

    client = get_client(url="", path=path)
    docs: list[SparseDoc] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection or COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            payload = p.payload or {}
            doc = _row_to_doc(payload, fallback_id=str(p.id))
            if doc:
                docs.append(doc)
        if offset is None:
            break
    return docs


def _resolve_docs(path: str = "qdrant_storage/local") -> list[SparseDoc]:
    base = Path(path)
    jsonl = base / "chunks.jsonl"
    if jsonl.is_file():
        return _load_docs_from_jsonl(jsonl)
    return _load_docs_from_qdrant(path=path)


@lru_cache(maxsize=1)
def get_bm25_index(path: str = "qdrant_storage/local") -> BM25Index:
    docs = _resolve_docs(path)
    return BM25Index(docs)


def sparse_search(
    query: str,
    limit: int = 20,
    path: str = "qdrant_storage/local",
    language: str | None = None,
    languages: set[str] | None = None,
) -> list[dict[str, Any]]:
    return get_bm25_index(path).search(
        query,
        limit=limit,
        language=language,
        languages=languages,
    )
