import json
from pathlib import Path

import pytest

from backend.core.languages import (
    ScriptGroupClassifier,
    detect_languages,
    looks_romanized_indic,
    normalize_code,
    reset_language_classifier,
    retrieval_languages,
    resolve_languages,
    train_language_classifier,
)
from backend.retrieval.sparse import BM25Index, SparseDoc

# The classifier is process-wide state that other tests train by running the
# pipeline, so every test here starts from a known, untrained baseline.
@pytest.fixture(autouse=True)
def _untrained_classifier():
    reset_language_classifier()
    yield
    reset_language_classifier()


CORPUS = Path("data/samples/deploy_msmarco_multilingual.jsonl")


def _corpus_samples() -> dict[str, list[str]]:
    samples: dict[str, list[str]] = {}
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        language = str(row.get("language") or "").strip().lower()
        passages = row.get("translated_passages") or row.get("english_passages") or []
        for passage in passages:
            if language and str(passage).strip():
                samples.setdefault(language, []).append(str(passage))
    return samples


needs_corpus = pytest.mark.skipif(not CORPUS.exists(), reason="language corpus not available")

QUERIES = {
    "en": "Where is Goa located?",
    "hi": "गोवा कहाँ है?",
    "mr": "गोवा कुठे आहे?",
    "sa": "गोवा कुत्र अस्ति?",
    "bn": "গোয়া কোথায়?",
    "as": "গোৱা ক'ত আছে?",
    "gu": "ગોવા ક્યાં છે?",
    "kn": "ಗೋವಾ ಎಲ್ಲಿದೆ?",
    "ml": "ഗോവ എവിടെയാണ്?",
    "or": "ଗୋଆ କେଉଁଠି ଅଛି?",
    "pa": "ਗੋਆ ਕਿੱਥੇ ਹੈ?",
    "ta": "கோவா எங்கே உள்ளது?",
    "te": "గోవా ఎక్కడ ఉంది?",
    "ur": "گوا کہاں ہے؟",
}


@pytest.mark.parametrize(("lang", "query"), sorted(QUERIES.items()))
def test_script_detection_includes_spoken_language(lang: str, query: str):
    assert lang in detect_languages(query)


@pytest.mark.parametrize(("lang", "query"), sorted(QUERIES.items()))
def test_devanagari_and_bengali_scripts_are_disambiguated(lang: str, query: str):
    # Languages sharing a script must not collapse into one another.
    assert detect_languages(query) == {lang}


def test_forced_language_beats_script():
    assert resolve_languages("गोवा कहाँ है?", forced="mr") == {"mr"}


def test_forced_language_matching_the_script_filters_to_it():
    assert resolve_languages("ગોવા ક્યાં છે?", forced="gu") == {"gu"}


def test_forced_language_of_another_script_keeps_the_written_language():
    # Scribe sometimes transcribes spoken Gujarati into Devanagari. Filtering
    # to Gujarati alone would match no chunk, so the written language stays
    # eligible and the question is still answered.
    resolved = resolve_languages("गोवा कहाँ है?", forced="gu")
    assert "gu" in resolved
    assert "hi" in resolved


@pytest.mark.parametrize(
    ("reported", "expected"),
    [("guj", "gu"), ("hin", "hi"), ("eng", "en"), ("ory", "or"), ("en-US", "en"), ("HI", "hi")],
)
def test_iso_639_3_and_regional_tags_reduce_to_the_index_code(reported: str, expected: str):
    assert normalize_code(reported) == expected


def test_stt_hint_in_iso_639_3_still_narrows_a_shared_script():
    # Scribe reports "mar", the index stores "mr"; without normalisation the
    # hint never matched and Devanagari always fell back to Hindi.
    assert resolve_languages("गोवा", hint="mar") == {"mr"}


def test_stt_hint_is_ignored_when_it_contradicts_the_script():
    assert resolve_languages("Where is Goa located?", hint="ta") == {"en"}


def test_stt_hint_narrows_within_a_shared_script():
    ambiguous = "गोवा"
    assert len(detect_languages(ambiguous)) > 1
    assert resolve_languages(ambiguous, hint="ne") == {"ne"}


def test_retrieval_keeps_full_shared_script_family_without_a_hint():
    assert retrieval_languages("एन्जाइना कहाँ फैलिन्छ ?") == {
        "hi",
        "mr",
        "ne",
        "sa",
    }


def test_retrieval_hint_safely_narrows_shared_script_family():
    assert retrieval_languages("एन्जाइना कहाँ फैलिन्छ ?", hint="nep") == {"ne"}


def test_retrieval_forced_language_keeps_mismatched_written_script_as_fallback():
    resolved = retrieval_languages("गोवा कहाँ है?", forced="gu")
    assert resolved == {"gu", "hi", "mr", "ne", "sa"}


def test_language_marker_must_be_a_whole_word():
    # "है" occurs as characters inside the Nepali word "भएका"; substring
    # matching used to misclassify this sentence as Hindi.
    query = "क्यान्सर भएका वा भएका प्रसिद्ध व्यक्तिहरू"
    assert "ne" in detect_languages(query)
    assert "hi" in detect_languages(query)


@pytest.mark.parametrize(
    "query",
    ["Goa kya chhe", "goa kahan hai", "goa kuthe ahe", "goa engey ulladhu enna"],
)
def test_indic_questions_typed_in_latin_letters_are_recognised(query: str):
    assert looks_romanized_indic(query)


@pytest.mark.parametrize(
    "query",
    ["Where is Goa located?", "What is the weather in Goa today?", "ગોવા ક્યાં છે?"],
)
def test_plain_english_and_native_scripts_are_not_flagged_as_romanized(query: str):
    assert not looks_romanized_indic(query)


def test_classifier_abstains_until_it_has_been_trained():
    classifier = ScriptGroupClassifier()
    assert classifier.predict("क्यान्सर भएका वा भएका प्रसिद्ध व्यक्तिहरू", {"hi", "ne"}) is None


def test_classifier_prefers_the_language_whose_text_it_learned():
    classifier = ScriptGroupClassifier(min_chars=100, min_query_chars=10)
    classifier.fit({"xx": ["abab abab " * 30], "yy": ["cdcd cdcd " * 30]})
    prediction = classifier.predict("abab abab abab", {"xx", "yy"})
    assert prediction is not None
    language, margin = prediction
    assert language == "xx"
    assert margin > 0


def test_classifier_skips_languages_with_too_little_text():
    classifier = ScriptGroupClassifier(min_chars=1_000)
    classifier.fit({"xx": ["too short"], "yy": ["also too short"]})
    assert classifier.languages == set()


def test_classifier_abstains_on_queries_too_short_to_judge():
    classifier = ScriptGroupClassifier(min_chars=100, min_query_chars=40)
    classifier.fit({"xx": ["abab abab " * 30], "yy": ["cdcd cdcd " * 30]})
    assert classifier.predict("abab", {"xx", "yy"}) is None


@needs_corpus
def test_training_resolves_devanagari_that_marker_words_cannot():
    query = "क्यान्सर भएका वा भएका प्रसिद्ध व्यक्तिहरू"
    assert len(detect_languages(query)) > 1

    train_language_classifier(_corpus_samples())
    assert detect_languages(query) == {"ne"}


@needs_corpus
@pytest.mark.parametrize(("lang", "query"), sorted(QUERIES.items()))
def test_demo_questions_stay_correct_once_the_classifier_is_trained(lang: str, query: str):
    train_language_classifier(_corpus_samples())
    assert detect_languages(query) == {lang} or lang in detect_languages(query)


@needs_corpus
def test_marker_words_outrank_the_trained_model():
    # "कुठे" is Marathi beyond doubt; corpus statistics must not overturn it.
    train_language_classifier(_corpus_samples())
    assert detect_languages("गोवा कुठे आहे?") == {"mr"}


def test_language_filter_falls_back_when_index_lacks_the_language():
    docs = [
        SparseDoc("a", "Goa is a coastal state in India.", "", "semantic", "en", "english", 1),
        SparseDoc("b", "The weather forecast is unrelated.", "", "semantic", "en", "english", 2),
        SparseDoc("c", "New Delhi is the capital.", "", "semantic", "en", "english", 3),
    ]
    hits = BM25Index(docs).search("Where is Goa located?", languages={"hi"})
    assert hits and hits[0]["chunk_id"] == "a"
