"""Detect the script of a query so retrieval can be filtered without a dropdown.

Scribe reports the spoken language when `include_language_detection` is on, but
typed queries have no such signal. Unicode blocks identify the script, which is
enough to narrow retrieval; where several languages share a script (Devanagari:
Hindi / Marathi / Nepali / Sanskrit) all of them stay eligible and BM25 picks.
"""

from __future__ import annotations

import re

# Ordered so the first matching range wins for a given character.
_SCRIPTS: list[tuple[int, int, tuple[str, ...]]] = [
    (0x0900, 0x097F, ("hi", "mr", "ne", "sa")),  # Devanagari
    (0x0980, 0x09FF, ("bn", "as")),  # Bengali / Assamese
    (0x0A00, 0x0A7F, ("pa",)),  # Gurmukhi
    (0x0A80, 0x0AFF, ("gu",)),  # Gujarati
    (0x0B00, 0x0B7F, ("or",)),  # Odia
    (0x0B80, 0x0BFF, ("ta",)),  # Tamil
    (0x0C00, 0x0C7F, ("te",)),  # Telugu
    (0x0C80, 0x0CFF, ("kn",)),  # Kannada
    (0x0D00, 0x0D7F, ("ml",)),  # Malayalam
    (0x0600, 0x06FF, ("ur",)),  # Arabic (Urdu)
    (0x0750, 0x077F, ("ur",)),
]


# Function words that separate languages sharing one script. Interrogatives and
# copulas are the reliable signals in a short spoken question.
_MARKERS: dict[str, tuple[str, ...]] = {
    "hi": ("कहाँ", "कहां", "है", "हैं", "क्या", "कौन", "कब", "कैसे", "कितना", "नहीं", "और", "मैं"),
    "mr": ("कुठे", "आहे", "आहेत", "काय", "कोण", "कसे", "नाही", "आणि", "मी"),
    "ne": ("छ", "छन्", "छैन", "कस्तो", "हुन्छ", "तपाईं", "गर्नु"),
    "sa": ("अस्ति", "कुत्र", "किम्", "कथम्", "भवति", "तत्र", "यत्र", "एव"),
    # Bengali and Assamese share many ordinary words. Only use their distinct
    # "where" forms here; otherwise keep both eligible and let retrieval decide.
    "bn": ("কোথায়",),
    "as": ("ক'ত",),
}

# Characters used by one language of a shared script only.
_EXCLUSIVE_CHARS: dict[str, tuple[str, ...]] = {
    "as": ("ৰ", "ৱ"),  # Assamese ra / wa, absent from Bengali
}
_WORD = re.compile(r"[\w\u0900-\u0D7F\u0600-\u06FF']+", re.UNICODE)


def _refine(text: str, candidates: tuple[str, ...] | set[str]) -> set[str]:
    """Pick the single language of a shared script when its markers appear."""
    cands = set(candidates)
    if len(cands) < 2:
        return cands

    for lang, chars in _EXCLUSIVE_CHARS.items():
        if lang in cands and any(c in text for c in chars):
            return {lang}

    words = set(_WORD.findall(text))
    scores = {
        lang: sum(1 for word in _MARKERS.get(lang, ()) if word in words)
        for lang in cands
    }
    best = max(scores.values())
    if best == 0:
        return cands
    winners = {lang for lang, score in scores.items() if score == best}
    return winners


def detect_languages(text: str) -> set[str]:
    """Languages whose script matches `text`; empty set means "do not filter"."""
    counts: dict[tuple[str, ...], int] = {}
    latin = 0
    for ch in text or "":
        if not ch.isalpha():
            continue
        code = ord(ch)
        if code < 0x0250:
            latin += 1
            continue
        for start, end, langs in _SCRIPTS:
            if start <= code <= end:
                counts[langs] = counts.get(langs, 0) + 1
                break

    if not counts:
        return {"en"} if latin else set()

    best = max(counts, key=lambda k: counts[k])
    refined = _refine(text, best)
    # Mixed scripts (e.g. an English word inside a Hindi question) still resolve
    # to the dominant non-Latin script, but keep English eligible when it leads.
    if latin > counts[best]:
        return {"en", *refined}
    return refined


def resolve_languages(
    text: str,
    *,
    forced: str | None = None,
    hint: str | None = None,
) -> set[str]:
    """Languages retrieval may use, in order of trust.

    A forced choice wins. Otherwise the script of the text decides, and a hint
    from speech recognition only narrows it further when the two agree — a
    misdetected language cannot pull retrieval away from what was written.
    """
    if forced and forced.strip():
        return {forced.strip().lower()}

    scripts = detect_languages(text)
    code = (hint or "").strip().lower().split("-")[0]
    if code and scripts and code in scripts:
        return {code}
    return scripts
