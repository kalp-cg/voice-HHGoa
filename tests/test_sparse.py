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
