from backend.retrieval.sparse import BM25Index, SparseDoc


def test_bm25_ranks_exact_term_first():
    docs = [
        SparseDoc("a", "Goa is a coastal state in India.", "Goa is a coastal state in India.", "semantic", "en", "english", 1),
        SparseDoc("b", "The weather forecast is unrelated.", "The weather forecast is unrelated.", "semantic", "en", "english", 2),
        SparseDoc("c", "New Delhi is the capital.", "New Delhi is the capital.", "semantic", "en", "english", 3),
    ]
    hits = BM25Index(docs).search("Where is Goa located?", limit=2)
    assert hits
    assert hits[0]["chunk_id"] == "a"
    assert hits[0]["score"] > hits[-1]["score"]


def test_source_query_indexes_translation_without_exposing_it_as_passage():
    docs = [
        SparseDoc(
            "relevant",
            "सेलिब्रिटीहरूले क्यान्सरसँग लड्दैछन्।",
            "",
            "semantic",
            "ne",
            "translated",
            1,
            search_text=(
                "क्यान्सर भएका प्रसिद्ध व्यक्तिहरू "
                "सेलिब्रिटीहरूले क्यान्सरसँग लड्दैछन्।"
            ),
            source_query="क्यान्सर भएका प्रसिद्ध व्यक्तिहरू",
        ),
        SparseDoc(
            "other",
            "अर्को असम्बन्धित अनुच्छेद।",
            "",
            "semantic",
            "ne",
            "translated",
            2,
        ),
    ]
    hits = BM25Index(docs).search("क्यान्सर भएका प्रसिद्ध व्यक्तिहरू")
    assert hits[0]["chunk_id"] == "relevant"
    assert hits[0]["text"] == "सेलिब्रिटीहरूले क्यान्सरसँग लड्दैछन्।"
    assert hits[0]["_source_query"] == "क्यान्सर भएका प्रसिद्ध व्यक्तिहरू"


_GUJARATI_PASSAGES = {
    "goa": "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે આવેલું એક રાજ્ય છે.",
    "boiling": "પાણીનું ઉકળવાનું તાપમાન 100 ડિગ્રી સેલ્સિયસ છે.",
    "lawyer": "વકીલની ફી સામાન્ય રીતે કલાકના દરે વસૂલવામાં આવે છે.",
    "glucose": "ગ્લુકોઝ એ શરીરની ઊર્જાનો મુખ્ય સ્રોત છે.",
    "gujarat": "ગુજરાત ભારતના પશ્ચિમ ભાગમાં આવેલું રાજ્ય છે.",
    "song": "આ ગીતનું રેકોર્ડિંગ 1998 માં થયું હતું.",
}


def _gujarati_index() -> BM25Index:
    # BM25 gives a term zero weight once it appears in most of the corpus, so
    # these assertions need more than a couple of passages to be meaningful.
    return BM25Index(
        [
            SparseDoc(cid, text, "", "semantic", "gu", "translated", i)
            for i, (cid, text) in enumerate(_GUJARATI_PASSAGES.items())
        ]
    )


def test_latin_name_in_an_indic_question_finds_the_native_passage():
    hits = _gujarati_index().search("Goa કયાં છે?")
    assert hits
    assert hits[0]["chunk_id"] == "goa"


def test_cross_script_expansion_does_not_inject_false_friends():
    extra = _gujarati_index()._cross_script_terms(["goa", "કયાં", "છે"], "Goa કયાં છે?")
    assert "ગોવા" in extra
    assert "ખોટા" not in extra
    assert "ગોળા" not in extra


def test_single_script_queries_skip_cross_script_expansion():
    """Expansion is recall-only, so it must not disturb same-script ranking."""
    hits = _gujarati_index().search("ઉકળવાનું તાપમાન")
    assert hits[0]["chunk_id"] == "boiling"


def test_mixed_indic_query_only_expands_the_latin_name():
    extra = _gujarati_index()._cross_script_terms(
        ["goa", "કયાં", "છે"],
        "Goa કયાં છે?",
        languages={"gu"},
    )
    assert extra == ["ગોવા"]


def test_same_script_content_words_are_not_expanded():
    extra = _gujarati_index()._cross_script_terms(
        ["प्रत्येक", "राज्य", "प्रतिनिधित्व", "आधार"],
        "प्रत्येक राज्य को प्रतिनिधित्व किस आधार पर होता है?",
        languages={"hi"},
    )
    assert extra == []
