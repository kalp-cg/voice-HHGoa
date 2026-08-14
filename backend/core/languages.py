"""Decide which languages a query may be retrieved in.

Signals are applied strongest-first, because they are not equally reliable:

1. Unicode block — exact, but only identifies the *script*. Gujarati, Tamil and
   Urdu are settled here; Devanagari and Bengali are shared by several
   languages and are not.
2. Function words unique to one language of a shared script — high precision,
   but only cover words someone thought to list.
3. Character n-gram profiles learned from the indexed text of each language —
   covers whatever the corpus actually contains, and is used only when the
   first two leave more than one candidate.
4. The language speech recognition reported — a guess about audio, so it only
   breaks ties inside a script it agrees with.

A language the user picked explicitly overrides all of it.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

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

# Scribe reports ISO 639-3 ("guj"), the index stores ISO 639-1 ("gu"). Without
# this mapping every spoken-language hint silently fails to match.
_ISO3_TO_ISO1 = {
    "asm": "as",
    "ben": "bn",
    "eng": "en",
    "guj": "gu",
    "hin": "hi",
    "kan": "kn",
    "kok": "kok",
    "gom": "kok",
    "mal": "ml",
    "mar": "mr",
    "nep": "ne",
    "ori": "or",
    "ory": "or",
    "pan": "pa",
    "san": "sa",
    "tam": "ta",
    "tel": "te",
    "urd": "ur",
}


def normalize_code(code: str | None) -> str:
    """Reduce a language tag to the ISO 639-1 code the index is keyed by."""
    base = (code or "").strip().lower().replace("_", "-").split("-")[0]
    return _ISO3_TO_ISO1.get(base, base)


# Romanised question words. Speech recognition sometimes writes an Indic
# question in Latin letters ("goa kya chhe"); no native-script passage can match
# that, so it is worth recognising in order to explain the failure.
_ROMANIZED_MARKERS = frozenset(
    {
        "ache", "ahe", "aahe", "ala", "che", "chha", "chhe", "cha",
        "ekkada", "elli", "ellide", "emiti", "enge", "engey", "enna", "enthu",
        "evide", "hai", "hain", "kaha", "kahan", "kaisa", "kaise", "kan",
        "kaun", "kay", "keu", "kithe", "kitna", "kon", "kot", "kothay",
        "kouthi", "kuthe", "kya", "kyaan", "kyan", "nahi", "nahin", "shu",
        "undi", "unnadi",
    }
)


def looks_romanized_indic(text: str) -> bool:
    """True when Latin-script text uses Indic question words."""
    script, _, latin = _dominant_script(text)
    if script is not None or not latin:
        return False
    words = {word.lower() for word in _WORD.findall(text or "")}
    return bool(words & _ROMANIZED_MARKERS)


# Question words and copulas for languages that own their script outright.
# `_MARKERS` only needs the shared-script languages; these exist to recognise a
# language by *sound* after speech recognition has written it in some other
# script, so they are compared in romanised form.
_SPOKEN_MARKERS: dict[str, tuple[str, ...]] = {
    "gu": ("ક્યાં", "છે", "શું", "કોણ", "કેમ", "કેટલું", "નથી", "અને"),
    "hi": ("कहाँ", "कहां", "है", "हैं", "क्या", "कौन", "कैसे", "कितना", "नहीं"),
    "mr": ("कुठे", "आहे", "आहेत", "काय", "कोण", "कसे", "नाही"),
    "ne": ("छ", "छन्", "छैन", "कस्तो", "हुन्छ"),
    "sa": ("अस्ति", "कुत्र", "किम्", "कथम्", "भवति"),
    "bn": ("কোথায়", "আছে", "কী", "কে", "কেমন"),
    "as": ("ক'ত", "আছে", "কি", "কোন"),
    "pa": ("ਕਿੱਥੇ", "ਹੈ", "ਕੀ", "ਕੌਣ", "ਕਿਵੇਂ"),
    "or": ("କେଉଁଠି", "ଅଛି", "କଣ", "କିଏ"),
    "ta": ("எங்கே", "என்ன", "உள்ளது", "யார்", "எப்படி"),
    "te": ("ఎక్కడ", "ఏమిటి", "ఉంది", "ఎవరు", "ఎలా"),
    "kn": ("ಎಲ್ಲಿ", "ಇದೆ", "ಏನು", "ಯಾರು", "ಹೇಗೆ"),
    "ml": ("എവിടെ", "എന്ത്", "ആണ്", "ആര്", "എങ്ങനെ"),
    "ur": ("کہاں", "ہے", "کیا", "کون", "کیسے"),
}


def _romanized_marker_index() -> dict[str, frozenset[str]]:
    from backend.core.translit import fold_roman, romanize_token

    return {
        code: frozenset(
            fold_roman(romanize_token(word)) for word in words if word
        )
        for code, words in _SPOKEN_MARKERS.items()
    }


_SPOKEN_BY_SOUND = _romanized_marker_index()


def spoken_language(text: str) -> str | None:
    """Language whose question words `text` sounds like, whatever script it uses.

    Speech recognition picks a language from audio before any text exists, and
    Indic languages that sound alike are routinely confused — spoken Gujarati
    is commonly written out in Devanagari as Hindi. The words themselves still
    carry the answer, so romanising them recovers the language that was
    actually spoken. Returns None unless one language wins outright.
    """
    from backend.core.translit import fold_roman, romanize_token

    words = {
        fold_roman(romanize_token(word)) for word in _WORD.findall(text or "")
    }
    words.discard("")
    if not words:
        return None
    hits = {
        code: len(words & markers)
        for code, markers in _SPOKEN_BY_SOUND.items()
        if words & markers
    }
    if not hits:
        return None
    best = max(hits.values())
    winners = [code for code, count in hits.items() if count == best]
    # `hai` belongs to Hindi, Punjabi and Urdu alike. An ambiguous vote is no
    # evidence, so leave the decision to the script and to retrieval.
    return winners[0] if len(winners) == 1 else None


_WHITESPACE = re.compile(r"\s+")


def _profile_text(text: str) -> str:
    """Normalise for n-gram counting; padding makes word edges countable."""
    collapsed = _WHITESPACE.sub(" ", (text or "").lower()).strip()
    return f" {collapsed} " if collapsed else ""


def _ngrams(text: str, order: int) -> list[str]:
    if len(text) < order:
        return []
    return [text[i : i + order] for i in range(len(text) - order + 1)]


@dataclass(frozen=True)
class _OrderModel:
    """Smoothed log P(ngram | language) for one n-gram order."""

    log_probs: dict[str, float]
    unseen: float


class ScriptGroupClassifier:
    """Separate languages that share a script, using the indexed corpus.

    Unicode ranges cannot tell Hindi from Marathi, and a hand-written word list
    only recognises the words it lists. Character n-gram profiles built from
    each language's own indexed text generalise to the rest of the corpus.

    Untrained, `predict` abstains, so callers keep their existing behaviour.
    """

    def __init__(
        self,
        *,
        orders: Sequence[int] = (1, 2, 3),
        alpha: float = 0.5,
        char_budget: int = 60_000,
        min_chars: int = 400,
        min_query_chars: int = 20,
    ) -> None:
        self._orders = tuple(orders)
        self._alpha = alpha
        self._char_budget = char_budget
        self._min_chars = min_chars
        self._min_query_chars = min_query_chars
        self._models: dict[str, dict[int, _OrderModel]] = {}

    @property
    def languages(self) -> set[str]:
        return set(self._models)

    def fit(self, samples: Mapping[str, Iterable[str]]) -> None:
        """Learn one profile per language from labelled text.

        Each language contributes at most `char_budget` characters so that a
        large index cannot make start-up slow, and languages with too little
        text are skipped rather than modelled badly.
        """
        corpus: dict[str, list[str]] = {}
        sizes: dict[str, int] = {}
        for language, texts in samples.items():
            code = normalize_code(language)
            if not code:
                continue
            bucket = corpus.setdefault(code, [])
            for text in texts:
                if sizes.get(code, 0) >= self._char_budget:
                    break
                normalized = _profile_text(text)
                if len(normalized) <= 2:
                    continue
                bucket.append(normalized)
                sizes[code] = sizes.get(code, 0) + len(normalized)

        models: dict[str, dict[int, _OrderModel]] = {}
        for code, texts in corpus.items():
            if sizes.get(code, 0) < self._min_chars:
                continue
            per_order: dict[int, _OrderModel] = {}
            for order in self._orders:
                counts: Counter[str] = Counter()
                for text in texts:
                    counts.update(_ngrams(text, order))
                if not counts:
                    continue
                total = sum(counts.values())
                denominator = total + self._alpha * (len(counts) + 1)
                per_order[order] = _OrderModel(
                    log_probs={
                        gram: math.log((count + self._alpha) / denominator)
                        for gram, count in counts.items()
                    },
                    unseen=math.log(self._alpha / denominator),
                )
            if per_order:
                models[code] = per_order
        self._models = models

    def _score(self, code: str, text: str) -> float | None:
        """Mean log-likelihood per n-gram, averaged over orders."""
        per_order = self._models.get(code)
        if not per_order:
            return None
        totals: list[float] = []
        for order, model in per_order.items():
            grams = _ngrams(text, order)
            if not grams:
                continue
            total = sum(model.log_probs.get(gram, model.unseen) for gram in grams)
            totals.append(total / len(grams))
        if not totals:
            return None
        return sum(totals) / len(totals)

    def predict(
        self, text: str, candidates: Iterable[str]
    ) -> tuple[str, float] | None:
        """Best candidate and its margin over the runner-up, or None.

        Short queries carry too few n-grams to separate related languages, and
        a confident-looking margin over three words is mostly noise.
        """
        normalized = _profile_text(text)
        if len(normalized) < self._min_query_chars:
            return None
        scored: list[tuple[float, str]] = []
        for code in candidates:
            score = self._score(code, normalized)
            if score is not None:
                scored.append((score, code))
        if len(scored) < 2:
            return None
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][1], scored[0][0] - scored[1][0]


# Margin in nats per n-gram. Chosen by sweeping thresholds over the indexed
# queries of the shared-script languages: at 0.25 (with the 20-character
# minimum) every misclassification in that sample is refused, with the closest
# one at 0.194. Below this the corpus does not separate the candidates, so
# every language of the script stays eligible and retrieval decides.
MIN_CLASSIFIER_MARGIN = 0.25

_classifier = ScriptGroupClassifier()


def train_language_classifier(samples: Mapping[str, Iterable[str]]) -> set[str]:
    """Fit the shared-script classifier; returns the languages it can judge."""
    _classifier.fit(samples)
    return _classifier.languages


def reset_language_classifier() -> None:
    _classifier.fit({})


def _refine(text: str, candidates: tuple[str, ...] | set[str]) -> set[str]:
    """Narrow languages sharing one script to the one actually written."""
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
    if best:
        # Markers are hand-verified, so when several of them match, lexical
        # retrieval across those languages beats a statistical tie-break.
        return {lang for lang, score in scores.items() if score == best}

    # No marker matched. Corpus statistics decide, if they are decisive.
    prediction = _classifier.predict(text, cands)
    if prediction is not None:
        language, margin = prediction
        if margin >= MIN_CLASSIFIER_MARGIN:
            return {language}
    return cands


def _dominant_script(text: str) -> tuple[tuple[str, ...] | None, int, int]:
    """Dominant non-Latin script of `text` with its character count and Latin count."""
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
        return None, 0, latin
    best = max(counts, key=lambda k: counts[k])
    return best, counts[best], latin


def script_languages(text: str) -> set[str]:
    """Every language of the script `text` is written in, before refinement.

    Marker refinement may produce a useful display label, but retrieval keeps
    the complete script family unless speech recognition or the user supplied
    a language. Excluding the correct language is worse than searching a few
    extra same-script passages.
    """
    best, best_count, latin = _dominant_script(text)
    if best is None:
        return {"en"} if latin else set()
    if latin > best_count:
        return {"en", *best}
    return set(best)


def detect_languages(text: str) -> set[str]:
    """Languages whose script matches `text`; empty set means "do not filter"."""
    best, best_count, latin = _dominant_script(text)
    if best is None:
        return {"en"} if latin else set()

    refined = _refine(text, best)
    # Mixed scripts (e.g. an English word inside a Hindi question) still resolve
    # to the dominant non-Latin script, but keep English eligible when it leads.
    if latin > best_count:
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

    When the hint *disagrees* with the script (e.g. Scribe heard Gujarati but
    transcribed in Devanagari), the hint is still included so that retrieval
    can search both the heard language and the written-script languages.
    Excluding the hint entirely caused zero-result failures for Gujarati,
    Assamese, and other languages that Scribe occasionally mis-scripts.
    """
    forced_code = normalize_code(forced)
    if forced_code:
        family = script_languages(text)
        # Speech recognition sometimes writes the wrong script (Gujarati heard
        # as Devanagari). Filtering to a language the transcript cannot match
        # would retrieve nothing, so keep the written languages eligible too.
        if family and forced_code not in family:
            return {forced_code, *detect_languages(text)}
        return {forced_code}

    scripts = detect_languages(text)
    # What the words say outranks the language speech recognition guessed from
    # audio: Gujarati written out in Devanagari still reads as Gujarati, and an
    # audio guess should never overrule the words themselves.
    sounds_like = spoken_language(text)
    if sounds_like:
        return {sounds_like} if sounds_like in scripts else {sounds_like, *scripts}

    code = normalize_code(hint)
    if code:
        if scripts and code in scripts:
            # Hint agrees with script — narrow to just the hinted language.
            return {code}
        # Hint disagrees with script — Scribe may have heard the right
        # language but transcribed in the wrong script. Include both so
        # retrieval has a chance to find passages in either.
        if scripts:
            return {code, *scripts}
        return {code}
    return scripts


def retrieval_languages(
    text: str,
    *,
    forced: str | None = None,
    hint: str | None = None,
) -> set[str]:
    """High-recall language candidates used to filter retrieval.

    A classifier can confidently label a mixed Hindi/Nepali sentence as the
    wrong one. For retrieval, keep every language sharing the written script
    unless the user forced one or Scribe supplied a compatible language hint.

    When the hint disagrees with the script family, include both: the heard
    language and every language of the written script. This prevents Gujarati
    speech transcribed in Devanagari from losing access to Gujarati passages.
    """
    family = script_languages(text)
    forced_code = normalize_code(forced)
    if forced_code:
        if family and forced_code not in family:
            return {forced_code, *family}
        return {forced_code}

    # Recognised as one language but worded like another: search both, because
    # only the passages of the language actually spoken can answer. When the
    # words agree with the script, they already settle it and an audio guess
    # must not narrow retrieval away from them.
    sounds_like = spoken_language(text)
    if sounds_like:
        if family and sounds_like not in family:
            return {sounds_like, *family}
        if family:
            return family

    hint_code = normalize_code(hint)
    if hint_code:
        if family and hint_code in family:
            return {hint_code}
        # Hint disagrees with the written script — include both.
        if family:
            return {hint_code, *family}
        return {hint_code}
    return family
