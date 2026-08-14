import pytest

from backend.core.languages import detect_languages, resolve_languages
from backend.retrieval.sparse import BM25Index, SparseDoc

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


def test_stt_hint_is_ignored_when_it_contradicts_the_script():
    assert resolve_languages("Where is Goa located?", hint="ta") == {"en"}


def test_stt_hint_narrows_within_a_shared_script():
    ambiguous = "गोवा"
    assert len(detect_languages(ambiguous)) > 1
    assert resolve_languages(ambiguous, hint="ne") == {"ne"}


def test_language_filter_falls_back_when_index_lacks_the_language():
    docs = [
        SparseDoc("a", "Goa is a coastal state in India.", "", "semantic", "en", "english", 1),
        SparseDoc("b", "The weather forecast is unrelated.", "", "semantic", "en", "english", 2),
        SparseDoc("c", "New Delhi is the capital.", "", "semantic", "en", "english", 3),
    ]
    hits = BM25Index(docs).search("Where is Goa located?", languages={"hi"})
    assert hits and hits[0]["chunk_id"] == "a"
