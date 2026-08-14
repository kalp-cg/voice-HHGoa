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
