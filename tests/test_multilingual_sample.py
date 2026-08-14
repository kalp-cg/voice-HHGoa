from scripts.build_multilingual_sample import (
    _answer_supported_by_passage,
    _has_clean_native_script,
)


def test_native_script_filter_accepts_clean_gujarati():
    assert _has_clean_native_script(
        "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે આવેલું રાજ્ય છે.",
        "gu",
        minimum_chars=10,
    )


def test_native_script_filter_rejects_bengali_text_labelled_odia():
    assert not _has_clean_native_script(
        "ফরেনসিক টক্সিকোলজিস্ট হওয়ার প্রয়োজনীয়তা",
        "or",
        minimum_chars=2,
    )


def test_native_script_filter_allows_latin_technical_terms():
    assert _has_clean_native_script(
        "IPsec નો ઉપયોગ IPv4 ટ્રાફિક સુરક્ષિત કરવા માટે થાય છે.",
        "gu",
        minimum_chars=10,
    )


def test_answer_passage_filter_accepts_supported_pair():
    assert _answer_supported_by_passage(
        "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે છે.",
        "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે આવેલું એક રાજ્ય છે.",
    )


def test_answer_passage_filter_rejects_contradictory_pair():
    assert not _answer_supported_by_passage(
        "ഇത് യുണൈറ്റഡ് സ്റ്റേറ്റ്സിലെ ഏറ്റവും വലിയ ഭക്ഷ്യയോഗ്യമായ പഴമാണ്.",
        "നഖങ്ങളുള്ള ഒരു മൃഗത്തിന്റെ കാൽ പാവ് എന്നാണ് അറിയപ്പെടുന്നത്.",
    )
