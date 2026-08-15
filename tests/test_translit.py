"""Cross-script matching between Latin and Indic spellings."""

from __future__ import annotations

import pytest

from backend.core.translit import (
    fuzzy_equal,
    fuzzy_key,
    fuzzy_keys,
    is_indic,
    is_mixed_script,
    romanize,
    romanize_token,
)

# Every script in the deployed index spells the same place name differently.
GOA = {
    "hi": "गोवा",
    "mr": "गोवा",
    "ne": "गोवा",
    "sa": "गोवा",
    "gu": "ગોવા",
    "bn": "গোয়া",
    "as": "গোৱা",
    "pa": "ਗੋਆ",
    "or": "ଗୋଆ",
    "ta": "கோவா",
    "te": "గోవా",
    "kn": "ಗೋವಾ",
    "ml": "ഗോവ",
    "ur": "گوا",
}


@pytest.mark.parametrize("language,native", sorted(GOA.items()))
def test_latin_name_matches_every_indic_spelling(language: str, native: str) -> None:
    assert fuzzy_equal("goa", romanize_token(native)), language


@pytest.mark.parametrize("language,native", sorted(GOA.items()))
def test_matching_spellings_are_in_a_probed_bucket(language: str, native: str) -> None:
    """Callers probe `fuzzy_keys`, so a match outside them would never be tried."""
    native_roman = romanize_token(native)
    assert fuzzy_key(native_roman) in fuzzy_keys("goa"), language


def test_romanize_leaves_latin_alone() -> None:
    assert romanize("Goa 2026") == "goa 2026"


def test_romanize_handles_mixed_text() -> None:
    assert romanize("Goa ગોવા") == "goa gova"


def test_unrelated_words_do_not_match() -> None:
    for native in ("ગુજરાત", "ભારત", "મુંબઈ", "કોંકણ", "ખોટા", "ગોળા", "કોવ"):
        assert not fuzzy_equal("goa", romanize_token(native)), native


def test_inflected_native_form_still_matches_the_stem() -> None:
    assert fuzzy_equal("inda", romanize_token("ઈંડાને"))
    assert fuzzy_equal(romanize_token("इंडा"), romanize_token("ઈંડા"))


def test_short_tokens_never_fuzzy_match() -> None:
    assert not fuzzy_equal("go", "ga")
    assert fuzzy_equal("go", "go")


def test_long_words_are_rejected_before_comparison() -> None:
    assert not fuzzy_equal("goa", romanize_token("ગુણવત્તાયુક્ત"))


def test_is_mixed_script_detects_latin_inside_indic() -> None:
    assert is_mixed_script("Goa ક્યાં છે?")
    assert is_mixed_script("India की राजधानी क्या है?")


def test_is_mixed_script_ignores_single_script_and_digits() -> None:
    assert not is_mixed_script("Where is Goa located?")
    assert not is_mixed_script("ગોવા ક્યાં છે?")
    assert not is_mixed_script("ગોવા 2026 માં?")


def test_is_indic() -> None:
    assert is_indic("ગોવા")
    assert is_indic("گوا")
    assert not is_indic("Goa")
