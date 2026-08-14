#!/usr/bin/env python3
"""Build a tiny per-language MSMARCO sample for the live demo.

Does not download the 55.6 GB MSMARCO-XI dump. Uses:
- curated Goa/India facts in every listed language (speaker / YouTube demo)
- a few rows from the official small IndicMSMARCO benchmark (~1 MB/lang)
- a Sanskrit bootstrap, because IndicMSMARCO has no `sa` config
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]

LANGS = [
    "as",
    "bn",
    "gu",
    "hi",
    "kn",
    "ml",
    "mr",
    "ne",
    "or",
    "pa",
    "sa",
    "ta",
    "te",
    "ur",
]

GOA: dict[str, dict[str, str]] = {
    "en": {
        "query": "Where is Goa located?",
        "answer": "Goa is a state on the southwestern coast of India.",
        "passage": (
            "Goa is a state on the southwestern coast of India within the Konkan "
            "region, bounded by Maharashtra to the north and Karnataka to the east "
            "and south, with the Arabian Sea forming its western coast."
        ),
    },
    "hi": {
        "query": "गोवा कहाँ है?",
        "answer": "गोवा भारत के दक्षिण-पश्चिमी तट पर स्थित एक राज्य है।",
        "passage": "गोवा भारत के दक्षिण-पश्चिमी तट पर कोंकण क्षेत्र में स्थित एक राज्य है।",
    },
    "bn": {
        "query": "গোয়া কোথায়?",
        "answer": "গোয়া ভারতের দক্ষিণ-পশ্চিম উপকূলে অবস্থিত একটি রাজ্য।",
        "passage": "গোয়া ভারতের দক্ষিণ-পশ্চিম উপকূলে কঙ্কন অঞ্চলে অবস্থিত একটি রাজ্য।",
    },
    "mr": {
        "query": "गोवा कुठे आहे?",
        "answer": "गोवा भारताच्या दक्षिण-पश्चिम किनाऱ्यावरील एक राज्य आहे.",
        "passage": "गोवा भारताच्या दक्षिण-पश्चिम किनाऱ्यावरील कोकण प्रदेशातील एक राज्य आहे.",
    },
    "gu": {
        "query": "ગોવા ક્યાં છે?",
        "answer": "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે આવેલું એક રાજ્ય છે.",
        "passage": "ગોવા ભારતના દક્ષિણ-પશ્ચિમ કિનારે કોંકણ પ્રદેશમાં આવેલું એક રાજ્ય છે.",
    },
    "ta": {
        "query": "கோவா எங்கே உள்ளது?",
        "answer": "கோவா இந்தியாவின் தென்மேற்கு கடற்கரையில் உள்ள ஒரு மாநிலம்.",
        "passage": "கோவா இந்தியாவின் தென்மேற்கு கடற்கரையில் கொங்கண் பகுதியில் அமைந்துள்ள ஒரு மாநிலம்.",
    },
    "te": {
        "query": "గోవా ఎక్కడ ఉంది?",
        "answer": "గోవా భారతదేశం నైరుతి తీరంలో ఉన్న రాష్ట్రం.",
        "passage": "గోవా భారతదేశం నైరుతి తీరంలో కొంకణ్ ప్రాంతంలో ఉన్న రాష్ట్రం.",
    },
    "kn": {
        "query": "ಗೋವಾ ಎಲ್ಲಿದೆ?",
        "answer": "ಗೋವಾ ಭಾರತದ ನೈಋತ್ಯ ಕರಾವಳಿಯಲ್ಲಿರುವ ಒಂದು ರಾಜ್ಯ.",
        "passage": "ಗೋವಾ ಭಾರತದ ನೈಋತ್ಯ ಕರಾವಳಿಯಲ್ಲಿ ಕೊಂಕಣ ಪ್ರದೇಶದಲ್ಲಿರುವ ಒಂದು ರಾಜ್ಯ.",
    },
    "ml": {
        "query": "ഗോവ എവിടെയാണ്?",
        "answer": "ഗോവ ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ തീരത്തുള്ള ഒരു സംസ്ഥാനമാണ്.",
        "passage": "ഗോവ ഇന്ത്യയുടെ തെക്കുപടിഞ്ഞാറൻ തീരത്ത് കൊങ്കൺ മേഖലയിലുള്ള ഒരു സംസ്ഥാനമാണ്.",
    },
    "pa": {
        "query": "ਗੋਆ ਕਿੱਥੇ ਹੈ?",
        "answer": "ਗੋਆ ਭਾਰਤ ਦੇ ਦੱਖਣ-ਪੱਛਮੀ ਤੱਟ ਉੱਤੇ ਇੱਕ ਰਾਜ ਹੈ।",
        "passage": "ਗੋਆ ਭਾਰਤ ਦੇ ਦੱਖਣ-ਪੱਛਮੀ ਤੱਟ ਉੱਤੇ ਕੋਂਕਣ ਖੇਤਰ ਵਿੱਚ ਸਥਿਤ ਇੱਕ ਰਾਜ ਹੈ।",
    },
    "ur": {
        "query": "گوا کہاں ہے؟",
        "answer": "گوا بھارت کے جنوب مغربی ساحل پر ایک ریاست ہے۔",
        "passage": "گوا بھارت کے جنوب مغربی ساحل پر کونکن علاقے میں واقع ایک ریاست ہے۔",
    },
    "ne": {
        "query": "गोवा कहाँ छ?",
        "answer": "गोवा भारतको दक्षिण-पश्चिमी तटमा अवस्थित एक राज्य हो।",
        "passage": "गोवा भारतको दक्षिण-पश्चिमी तटमा कोङ्कण क्षेत्रमा अवस्थित एक राज्य हो।",
    },
    "or": {
        "query": "ଗୋଆ କେଉଁଠି ଅଛି?",
        "answer": "ଗୋଆ ଭାରତର ଦକ୍ଷିଣ-ପଶ୍ଚିମ ଉପକୂଳରେ ଥିବା ଏକ ରାଜ୍ୟ।",
        "passage": "ଗୋଆ ଭାରତର ଦକ୍ଷିଣ-ପଶ୍ଚିମ ଉପକୂଳରେ କୋଙ୍କଣ ଅଞ୍ଚଳରେ ଥିବା ଏକ ରାଜ୍ୟ।",
    },
    "as": {
        "query": "গোৱা ক'ত আছে?",
        "answer": "গোৱা ভাৰতৰ দক্ষিণ-পশ্চিম উপকূলত অৱস্থিত এখন ৰাজ্য।",
        "passage": "গোৱা ভাৰতৰ দক্ষিণ-পশ্চিম উপকূলত কোংকণ অঞ্চলত অৱস্থিত এখন ৰাজ্য।",
    },
    "sa": {
        "query": "गोवा कुत्र अस्ति?",
        "answer": "गोवा भारतस्य दक्षिणपश्चिमकूले स्थितं राज्यम् अस्ति।",
        "passage": "गोवा भारतस्य दक्षिणपश्चिमकूले कोङ्कणप्रदेशे स्थितं राज्यम् अस्ति।",
    },
}


def _record(
    *,
    query_id: int,
    language: str,
    query: str,
    answer: str,
    translated: str,
    english: str = "",
    eng_query: str = "",
    eng_answer: str = "",
) -> dict:
    return {
        "query_id": query_id,
        "query": query,
        "eng_query": eng_query or GOA["en"]["query"],
        "answer": answer,
        "eng_answer": eng_answer or GOA["en"]["answer"],
        "query_type": "LOCATION",
        "source_lang": "eng_Latn",
        "target_lang": language,
        "language": language,
        "english_passages": [english] if english else [GOA["en"]["passage"]],
        "translated_passages": [translated] if language != "en" else [],
        "is_selected": [1],
    }


def goa_records() -> list[dict]:
    rows = []
    for i, lang in enumerate(["en", *LANGS], start=9001):
        item = GOA[lang]
        rows.append(
            _record(
                query_id=i,
                language=lang,
                query=item["query"],
                answer=item["answer"],
                translated=item["passage"],
                english=GOA["en"]["passage"],
                eng_query=GOA["en"]["query"],
                eng_answer=GOA["en"]["answer"],
            )
        )
    return rows


def corpus_records(parquet_root: Path, per_lang: int) -> list[dict]:
    rows: list[dict] = []
    query_id = 9100
    for lang in LANGS:
        if lang == "sa":
            continue
        path = parquet_root / lang / "train-00000-of-00001.parquet"
        table = pq.read_table(path)
        taken = 0
        for raw in table.to_pylist():
            query = (raw.get("query") or "").strip()
            passage = (raw.get("passage") or "").strip()
            answer = (raw.get("answer") or "").strip()
            if len(query) < 4 or len(passage) < 40:
                continue
            query_id += 1
            rows.append(
                {
                    "query_id": query_id,
                    "query": query,
                    "eng_query": "",
                    "answer": answer,
                    "eng_answer": "",
                    "query_type": str(raw.get("query_type") or "DESCRIPTION"),
                    "source_lang": "eng_Latn",
                    "target_lang": lang,
                    "language": lang,
                    "english_passages": [],
                    "translated_passages": [passage],
                    "is_selected": [1],
                }
            )
            taken += 1
            if taken >= per_lang:
                break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parquet-root",
        type=Path,
        default=Path("/tmp/indic-msmarco-mini"),
    )
    parser.add_argument(
        "--per-lang",
        type=int,
        default=15,
        help="Official IndicMSMARCO rows per language (Sanskrit uses curated data only).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data/samples/deploy_msmarco_multilingual.jsonl",
    )
    args = parser.parse_args()

    rows = goa_records()
    if args.per_lang > 0:
        rows += corpus_records(args.parquet_root, args.per_lang)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["language"]] = counts.get(row["language"], 0) + 1
    print(
        json.dumps(
            {
                "output": str(args.out),
                "records": len(rows),
                "languages": counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
