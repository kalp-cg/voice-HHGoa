"""Stream a capped sample from ai4bharat/MSMARCO-XI without loading 56GB.

Hub layout uses per-language parquet under train/ (e.g. train/hintrain.parquet).
The datasets builder only exposes config 'default', so we stream by data_files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

from datasets import load_dataset

DATASET_ID = "ai4bharat/MSMARCO-XI"

# Map short language codes → parquet filenames on the Hub
LANG_TRAIN_FILES = {
    "as": "train/asmtrain.parquet",
    "bn": "train/bentrain.parquet",
    "gu": "train/gujtrain.parquet",
    "hi": "train/hintrain.parquet",
    "kn": "train/kantrain.parquet",
    "ml": "train/maltrain.parquet",
    "mr": "train/martrain.parquet",
    "ne": "train/neptrain.parquet",
    "or": "train/oritrain.parquet",
    "pa": "train/pantrain.parquet",
    "sa": "train/santrain.parquet",
    "ta": "train/tamtrain.parquet",
    "ur": "train/urdtrain.parquet",
}


def parquet_url(language: str, split: str = "train") -> str:
    lang = language.lower()
    if split == "train":
        rel = LANG_TRAIN_FILES.get(lang)
        if not rel:
            raise ValueError(
                f"Unsupported language '{language}'. Choose from: {sorted(LANG_TRAIN_FILES)}"
            )
    else:
        # validation naming: hinval.parquet etc.
        prefix = {
            "as": "asm",
            "bn": "ben",
            "gu": "guj",
            "hi": "hin",
            "kn": "kan",
            "ml": "mal",
            "mr": "mar",
            "ne": "nep",
            "or": "ori",
            "pa": "pan",
            "sa": "san",
            "ta": "tam",
            "te": "tel",
            "ur": "urd",
        }.get(lang)
        if not prefix:
            raise ValueError(f"Unsupported language '{language}'")
        rel = f"validation/{prefix}val.parquet"
    return f"hf://datasets/{DATASET_ID}/{rel}"


def iter_examples(
    language: str = "hi",
    split: str = "train",
    limit: int = 10_000,
) -> Iterator[dict[str, Any]]:
    url = parquet_url(language, split)
    ds = load_dataset("parquet", data_files={"data": url}, split="data", streaming=True)
    for i, row in enumerate(ds):
        if i >= limit:
            break
        yield dict(row)


def normalize_record(row: dict[str, Any], language: str) -> dict[str, Any]:
    passages = row.get("passages") or {}
    if not isinstance(passages, dict):
        passages = {}
    eng = passages.get("English_passages") or []
    tr = passages.get("Translated_passages") or []
    selected = passages.get("is_selected") or []

    answer = row.get("Answer") or row.get("answers") or row.get("Eng_Answer") or ""
    if isinstance(answer, list):
        answer = " ".join(str(a) for a in answer)

    return {
        "query_id": row.get("query_id"),
        "query": row.get("query") or "",
        "eng_query": row.get("Eng_Query") or "",
        "answer": str(answer),
        "eng_answer": row.get("Eng_Answer") or "",
        "query_type": row.get("query_type") or "",
        "source_lang": row.get("source_lang") or "eng_Latn",
        "target_lang": row.get("target_lang") or "",
        "language": language,
        "english_passages": list(eng),
        "translated_passages": list(tr),
        "is_selected": list(selected),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect / sample MSMARCO-XI via streaming")
    parser.add_argument("--language", default="hi")
    parser.add_argument("--split", default="train")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    writer = None
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        writer = args.out.open("w", encoding="utf-8")

    try:
        for i, row in enumerate(iter_examples(args.language, args.split, args.limit)):
            rec = normalize_record(row, args.language)
            if writer:
                writer.write(json.dumps(rec, ensure_ascii=False) + "\n")
            else:
                print(f"--- example {i} ---")
                print("query_id:", rec["query_id"])
                print("query:", (rec["query"] or "")[:200])
                print("eng_query:", (rec["eng_query"] or "")[:200])
                print("answer:", (rec["answer"] or "")[:200])
                print("n_eng_passages:", len(rec["english_passages"]))
                print("n_tr_passages:", len(rec["translated_passages"]))
                if rec["english_passages"]:
                    print("passage0:", rec["english_passages"][0][:240])
                print("langs:", rec["source_lang"], "->", rec["target_lang"])
    finally:
        if writer:
            writer.close()
            print(f"Wrote {args.limit} records to {args.out}")


if __name__ == "__main__":
    main()
