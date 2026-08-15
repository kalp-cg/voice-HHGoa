from backend.core.telemetry import percentiles
from backend.generation.extractive import extractive_answer
from backend.guardrails.grounding import overlap_ratio, verify_grounding
from backend.guardrails.relevance import should_refuse
from backend.guardrails.safety import is_unsafe
from backend.retrieval.dedupe import dedupe_hits
from backend.retrieval.hybrid import reciprocal_rank_fusion
from ingestion.chunking import compact_index_chunks


def test_rrf_prefers_consensus():
    a = [{"chunk_id": "x", "text": "A", "score": 1}, {"chunk_id": "y", "text": "B", "score": 0.5}]
    b = [{"chunk_id": "y", "text": "B", "score": 1}, {"chunk_id": "x", "text": "A", "score": 0.4}]
    fused = reciprocal_rank_fusion([a, b], limit=2)
    assert fused[0]["chunk_id"] in {"x", "y"}
    assert len(fused) == 2


def test_dedupe_by_parent():
    hits = [
        {"chunk_id": "1", "parent_text": "New Delhi is the capital.", "text": "New Delhi is the capital."},
        {"chunk_id": "2", "parent_text": "New Delhi is the capital.", "text": "capital"},
        {"chunk_id": "3", "parent_text": "Goa is a state.", "text": "Goa is a state."},
    ]
    out = dedupe_hits(hits)
    assert len(out) == 2


def test_percentiles():
    p = percentiles([10, 20, 30, 40, 50], (50, 70, 100))
    assert p["p50"] == 30
    assert p["p100"] == 50


def test_unsafe_and_relevance():
    assert is_unsafe("how to make a bomb")
    assert not is_unsafe("What is the capital of India?")
    refuse, _, msg = should_refuse([], 0.2, "capital of india")
    assert refuse
    joke, _, _ = should_refuse([{"text": "jokes"}], 0.2, "Tell me a joke.")
    assert joke
    weather, _, _ = should_refuse([{"text": "rain"}], 0.2, "What's the weather in Goa today?")
    assert weather


def test_exact_benchmark_pair_is_relevant_across_translation_variants():
    query = "क्यान्सर भएका प्रसिद्ध व्यक्तिहरू"
    hits = [
        {
            "text": "सेलिब्रिटीहरूले क्यान्सरसँग लड्दैछन्।",
            "_source_query": query,
        }
    ]
    refuse, confidence, _ = should_refuse(hits, 0.2, query)
    assert not refuse
    assert confidence == 1.0


def test_latin_name_counts_as_covered_by_a_native_script_passage():
    hits = [{"text": "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે આવેલું એક રાજ્ય છે."}]
    refuse, confidence, _ = should_refuse(hits, 0.5, "Goa કયાં છે?")
    assert not refuse
    assert confidence >= 0.5


def test_cross_script_coverage_still_refuses_an_unrelated_passage():
    hits = [{"text": "પાણીનું ઉકળવાનું તાપમાન 100 ડિગ્રી સેલ્સિયસ છે."}]
    refuse, _, _ = should_refuse(hits, 0.5, "Goa કયાં છે?")
    assert refuse


def test_short_query_does_not_answer_from_a_partial_overlap():
    hits = [{"text": "Goa is a state on the southwestern coast of India."}]
    refuse, _, _ = should_refuse(hits, 0.5, "What is the capital of India?")
    assert refuse
    query = "What is the weather in Goa today?"
    hits = [{"text": "Goa is a state.", "_source_query": query}]
    refuse, _, _ = should_refuse(hits, 0.2, query)
    assert refuse


def test_grounding_overlap():
    hits = [{"parent_text": "New Delhi is the capital of India."}]
    ok, ratio, _ = verify_grounding("New Delhi is the capital of India.", hits, 0.2)
    assert ok
    assert ratio > 0.5
    bad, _, ans = verify_grounding("The stock market crashed 40 percent today.", hits, 0.4)
    assert not bad
    assert "enough information" in ans.lower()


def test_extractive_picks_capital():
    hits = [
        {
            "text": "India is in South Asia. New Delhi is its capital.",
            "parent_text": "India is in South Asia. New Delhi is its capital.",
            "score": 0.7,
        }
    ]
    ans = extractive_answer("What is the capital of India?", hits)
    assert "delhi" in ans.lower()


def test_compact_chunks_cover_records():
    recs = [
        {
            "query_id": 1,
            "query": "q",
            "eng_query": "q",
            "language": "en",
            "source_lang": "eng_Latn",
            "target_lang": "eng_Latn",
            "query_type": "X",
            "english_passages": ["India is a country in South Asia. New Delhi is its capital."],
            "translated_passages": [],
            "is_selected": [1],
        }
    ]
    chunks = compact_index_chunks(recs, max_chunks=10)
    assert chunks
    assert any("Delhi" in c.text or "Delhi" in c.parent_text for c in chunks)


def test_overlap_ratio_zero_on_empty():
    assert overlap_ratio("", "abc") == 0.0
