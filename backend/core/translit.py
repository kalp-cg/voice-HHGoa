"""Compare Latin and Indic spellings of the same word.

Questions are routinely typed and spoken with an English proper noun inside an
Indic sentence ("Goa કયાં છે?"). Lexical retrieval sees no shared characters
between `Goa` and `ગોવા`, so the passage that answers the question cannot be
found at all.

Every Brahmic script in this corpus uses the same ISCII-derived layout, so a
character can be shifted into Devanagari and romanised from one table. The
result is deliberately rough — `ગોવા` becomes `gova`, not `gōvā` — because it
is only ever compared, never displayed.
"""

from __future__ import annotations

from difflib import SequenceMatcher

# Start of each Brahmic block that shares Devanagari's ordering.
_BLOCK_BASES = (
    0x0900,  # Devanagari
    0x0980,  # Bengali / Assamese
    0x0A00,  # Gurmukhi
    0x0A80,  # Gujarati
    0x0B00,  # Odia
    0x0B80,  # Tamil
    0x0C00,  # Telugu
    0x0C80,  # Kannada
    0x0D00,  # Malayalam
)

_DEVANAGARI: dict[int, str] = {
    # Independent vowels
    0x0905: "a", 0x0906: "a", 0x0907: "i", 0x0908: "i", 0x0909: "u",
    0x090A: "u", 0x090B: "ri", 0x090F: "e", 0x0910: "ai", 0x0913: "o",
    0x0914: "au", 0x090D: "e", 0x0911: "o",
    # Consonants
    0x0915: "k", 0x0916: "kh", 0x0917: "g", 0x0918: "gh", 0x0919: "n",
    0x091A: "ch", 0x091B: "chh", 0x091C: "j", 0x091D: "jh", 0x091E: "n",
    0x091F: "t", 0x0920: "th", 0x0921: "d", 0x0922: "dh", 0x0923: "n",
    0x0924: "t", 0x0925: "th", 0x0926: "d", 0x0927: "dh", 0x0928: "n",
    0x092A: "p", 0x092B: "ph", 0x092C: "b", 0x092D: "bh", 0x092E: "m",
    0x092F: "y", 0x0930: "r", 0x0932: "l", 0x0933: "l", 0x0935: "v",
    0x0936: "sh", 0x0937: "sh", 0x0938: "s", 0x0939: "h",
    # Dependent vowel signs
    0x093E: "a", 0x093F: "i", 0x0940: "i", 0x0941: "u", 0x0942: "u",
    0x0943: "ri", 0x0947: "e", 0x0948: "ai", 0x094B: "o", 0x094C: "au",
    0x0946: "e", 0x094A: "o",
    # Nasalisation and visarga; virama joins consonants and adds nothing.
    0x0902: "n", 0x0901: "n", 0x0903: "h", 0x094D: "",
}

# Urdu is Perso-Arabic rather than Brahmic, so it needs its own table.
_ARABIC: dict[int, str] = {
    0x0627: "a", 0x0628: "b", 0x067E: "p", 0x062A: "t", 0x0679: "t",
    0x062B: "s", 0x062C: "j", 0x0686: "ch", 0x062D: "h", 0x062E: "kh",
    0x062F: "d", 0x0688: "d", 0x0630: "z", 0x0631: "r", 0x0691: "r",
    0x0632: "z", 0x0698: "zh", 0x0633: "s", 0x0634: "sh", 0x0635: "s",
    0x0636: "z", 0x0637: "t", 0x0638: "z", 0x0639: "a", 0x063A: "gh",
    0x0641: "f", 0x0642: "q", 0x06A9: "k", 0x0643: "k", 0x06AF: "g",
    # Urdu waw is both /o/ and /v/; the vowel reading is the common one and is
    # what makes گوا line up with "Goa".
    0x0644: "l", 0x0645: "m", 0x0646: "n", 0x06BA: "n", 0x0648: "o",
    0x06C1: "h", 0x0647: "h", 0x06CC: "y", 0x064A: "y", 0x06D2: "e",
}

_MIN_FUZZY_LENGTH = 3
# Only longer names use a ratio: on three- and four-letter words a single extra
# letter already scores 0.85, which is how `goa` was matching Gujarati `gola`.
_FUZZY_THRESHOLD = 0.8
_LONG_NAME = 5
_VOWELS = set("aeiou")

# Scripts disagree on voicing and aspiration for the same borrowed name — Tamil
# writes Goa with its k letter, Bengali inserts a glide. Folding each group to
# one letter compares the consonant skeleton instead of the spelling.
_FOLD = (
    ("chh", "c"), ("ch", "c"), ("jh", "c"), ("kh", "k"), ("gh", "k"),
    ("th", "t"), ("dh", "t"), ("ph", "p"), ("bh", "p"), ("sh", "s"),
    ("g", "k"), ("j", "c"), ("d", "t"), ("b", "p"), ("z", "s"),
    ("w", "v"), ("y", "i"),
)

# Glides appear or vanish between the same vowels across scripts: English Goa,
# Gujarati gova, Bengali goya, Malayalam gov. Dropping them compares what the
# spellings agree on.
_GLIDES = str.maketrans("", "", "vwyh")


def _fold(text: str) -> str:
    for src, dst in _FOLD:
        text = text.replace(src, dst)
    return text


def _skeleton(roman: str) -> str:
    return _fold(roman.translate(_GLIDES))


def _near(left: str, right: str) -> bool:
    """True when two skeletons are the same name, including a missing final vowel."""
    if left == right:
        return True
    if abs(len(left) - len(right)) != 1:
        return False
    longer, shorter = (left, right) if len(left) > len(right) else (right, left)
    return longer[-1] in _VOWELS and longer[:-1] == shorter


def _romanize_char(char: str) -> str | None:
    code = ord(char)
    mapped = _ARABIC.get(code)
    if mapped is not None:
        return mapped
    for base in _BLOCK_BASES:
        if base <= code < base + 0x80:
            return _DEVANAGARI.get(0x0900 + (code - base), "")
    return None


def romanize(text: str) -> str:
    """Rough Latin form of `text`; Latin characters pass through unchanged."""
    out: list[str] = []
    for char in text or "":
        mapped = _romanize_char(char)
        out.append(char.lower() if mapped is None else mapped)
    return "".join(out)


def romanize_token(token: str) -> str:
    if not token:
        return ""
    if token.isascii():
        return token.lower()
    return romanize(token)


def fold_roman(roman: str) -> str:
    """Collapse voicing and aspiration, so `enge` and `enke` compare equal."""
    return _fold(roman)


def fuzzy_key(roman: str) -> str:
    """Original first letter, so voiced and unvoiced names stay in separate buckets."""
    return roman[0] if roman else ""


def fuzzy_keys(roman: str) -> tuple[str, ...]:
    """Buckets a query word must probe: its own first letter, and the folded one.

    Tamil writes Goa with k, so a Latin `goa` has to look in the k bucket as
    well as the g bucket. Folding the index itself would merge those buckets
    and force every k-word through the matcher.
    """
    if not roman:
        return ()
    keys = [roman[0]]
    skeleton = _skeleton(roman)
    if skeleton and skeleton[0] not in keys:
        keys.append(skeleton[0])
    return tuple(keys)


def skeleton(roman: str) -> str:
    """Consonant skeleton used to look up the same name in another script."""
    return _skeleton(roman)


def related_skeletons(roman: str) -> tuple[str, ...]:
    """Skeletons that can still be the same name, including a missing final vowel.

    Retrieval indexes natives by skeleton so a query word is an O(1) lookup
    instead of SequenceMatcher against every word that shares a first letter.
    """
    skel = _skeleton(roman)
    if not skel:
        return ()
    keys = [skel]
    if skel[-1] in _VOWELS:
        stem = skel[:-1]
        if stem:
            keys.append(stem)
    else:
        keys.extend(skel + vowel for vowel in "aeiou")
    return tuple(dict.fromkeys(keys))


def is_indic(text: str) -> bool:
    return any(_romanize_char(char) is not None for char in text or "")


def fuzzy_equal(left: str, right: str) -> bool:
    """True when two romanised tokens are plausibly the same word."""
    return fuzzy_score(left, right) > 0.0


def fuzzy_score(left: str, right: str) -> float:
    """1.0 for an exact romanisation, lower for a folded or clipped spelling."""
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if len(left) < _MIN_FUZZY_LENGTH or len(right) < _MIN_FUZZY_LENGTH:
        return 0.0
    shorter, longer = sorted((len(left), len(right)))
    if longer > 2 * shorter:
        return 0.0
    skeleton_left, skeleton_right = _skeleton(left), _skeleton(right)
    if not skeleton_left or not skeleton_right:
        return 0.0
    if skeleton_left == skeleton_right:
        return 0.95
    # Inflection: `इंडा` vs `ઈંડાને`, `Goa` vs a declined native form.
    short_s, long_s = sorted((skeleton_left, skeleton_right), key=len)
    if (
        len(short_s) >= 4
        and long_s.startswith(short_s)
        and len(long_s) - len(short_s) <= 3
    ):
        return 0.88
    # A missing final vowel (Malayalam `gov` vs `goa`) is allowed only when
    # the spellings already share a first letter. Otherwise Gujarati `kov`
    # would count as Goa just because Tamil writes the same name with k.
    if left[0] == right[0] and _near(skeleton_left, skeleton_right):
        return 0.9
    if shorter < _LONG_NAME:
        return 0.0
    ratio = max(
        SequenceMatcher(None, left, right).ratio(),
        SequenceMatcher(None, skeleton_left, skeleton_right).ratio(),
    )
    return ratio if ratio >= _FUZZY_THRESHOLD else 0.0


def script_base(char: str) -> int | None:
    code = ord(char)
    for base in _BLOCK_BASES:
        if base <= code < base + 0x80:
            return base
    if 0x0600 <= code <= 0x06FF:
        return 0x0600
    return None


def scripts_in(text: str) -> frozenset[int]:
    return frozenset(b for char in text or "" if (b := script_base(char)) is not None)


def any_fuzzy_match(target: str, buckets: dict[str, list[str]]) -> bool:
    """True if `target` matches a romanised form in any of its probe buckets."""
    return any(
        fuzzy_equal(target, other)
        for key in fuzzy_keys(target)
        for other in buckets.get(key, ())
    )


def is_mixed_script(text: str) -> bool:
    """True when a question mixes Latin words into an Indic sentence."""
    has_latin = False
    has_indic = False
    for char in text or "":
        if not char.isalpha():
            continue
        if _romanize_char(char) is not None:
            has_indic = True
        elif char.isascii():
            has_latin = True
        if has_latin and has_indic:
            return True
    return False
