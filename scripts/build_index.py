#!/usr/bin/env python3
"""Build a capped MSMARCO-XI mini-index in Qdrant (default 10k records)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.chunking import records_to_chunks
from ingestion.clean import clean_record
from ingestion.embed import DEFAULT_MODEL, embed_texts
from ingestion.stream_dataset import iter_examples, normalize_record
from retrieval.qdrant import (
    COLLECTION,
    VECTOR_SIZE,
    ensure_collection,
    get_client,
    upsert_chunks,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="hi")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--qdrant-url", default="")
    parser.add_argument("--qdrant-path", default="qdrant_storage/local")
    parser.add_argument("--collection", default=COLLECTION)
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument(
        "--strategies",
        default="sentence,semantic,parent_child",
        help="Comma list: sentence,sliding,semantic,parent_child",
    )
    parser.add_argument("--sample-out", type=Path, default=Path("data/samples/msmarco_xi_hi_sample.jsonl"))
    parser.add_argument("--max-chunks", type=int, default=40_000)
    args = parser.parse_args()

    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]

    print(f"Streaming up to {args.limit} records ({args.language})…")
    t0 = time.perf_counter()
    records = []
    for row in iter_examples(args.language, "train", args.limit):
        rec = clean_record(normalize_record(row, args.language))
        if rec:
            records.append(rec)
    stream_s = time.perf_counter() - t0
    print(f"Kept {len(records)} clean records in {stream_s:.1f}s")

    args.sample_out.parent.mkdir(parents=True, exist_ok=True)
    with args.sample_out.open("w", encoding="utf-8") as f:
        for rec in records[:200]:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote sample preview → {args.sample_out}")

    print(f"Chunking with strategies={strategies}…")
    t1 = time.perf_counter()
    chunks = records_to_chunks(records, strategies=strategies)  # type: ignore[arg-type]
    if len(chunks) > args.max_chunks:
        print(f"Truncating chunks {len(chunks)} → {args.max_chunks}")
        chunks = chunks[: args.max_chunks]
    chunk_s = time.perf_counter() - t1
    print(f"{len(chunks)} chunks in {chunk_s:.1f}s")

    texts = [c.text for c in chunks]
    payloads = [c.payload() for c in chunks]

    print(f"Embedding with {DEFAULT_MODEL}…")
    t2 = time.perf_counter()
    vectors = embed_texts(texts)
    embed_s = time.perf_counter() - t2
    dim = len(vectors[0]) if vectors else VECTOR_SIZE
    print(f"Embedded {len(vectors)} vectors dim={dim} in {embed_s:.1f}s")

    client = get_client(url=args.qdrant_url, path=args.qdrant_path)
    ensure_collection(client, args.collection, vector_size=dim, recreate=args.recreate)
    t3 = time.perf_counter()
    n = upsert_chunks(client, texts, vectors, payloads, collection=args.collection)
    upsert_s = time.perf_counter() - t3
    print(f"Upserted {n} points into '{args.collection}' in {upsert_s:.1f}s")

    manifest = {
        "dataset": "ai4bharat/MSMARCO-XI",
        "language": args.language,
        "records": len(records),
        "chunks": len(chunks),
        "collection": args.collection,
        "embedding_model": DEFAULT_MODEL,
        "vector_dim": dim,
        "strategies": strategies,
        "timings_s": {
            "stream": stream_s,
            "chunk": chunk_s,
            "embed": embed_s,
            "upsert": upsert_s,
        },
    }
    manifest_path = Path("data/manifests/mini_index.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest → {manifest_path}")
    print("DONE")


if __name__ == "__main__":
    main()
