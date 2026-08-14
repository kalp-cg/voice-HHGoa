#!/usr/bin/env python3
"""Build Qdrant mini-index from a local JSONL sample (bootstrap or exported)."""

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
from retrieval.qdrant import (
    COLLECTION,
    VECTOR_SIZE,
    ensure_collection,
    get_client,
    upsert_chunks,
)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = clean_record(json.loads(line))
            if rec:
                rows.append(rec)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/samples/bootstrap_msmarco.jsonl"))
    parser.add_argument("--qdrant-path", default="qdrant_storage/local")
    parser.add_argument("--collection", default=COLLECTION)
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument(
        "--strategies",
        default="sentence,semantic,parent_child,sliding",
    )
    parser.add_argument("--max-chunks", type=int, default=20_000)
    args = parser.parse_args()

    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    records = load_jsonl(args.input)
    print(f"Loaded {len(records)} records from {args.input}")

    chunks = records_to_chunks(records, strategies=strategies)  # type: ignore[arg-type]
    if len(chunks) > args.max_chunks:
        chunks = chunks[: args.max_chunks]
    print(f"{len(chunks)} chunks strategies={strategies}")

    texts = [c.text for c in chunks]
    payloads = [c.payload() for c in chunks]

    t0 = time.perf_counter()
    vectors = embed_texts(texts)
    print(f"Embedded in {time.perf_counter()-t0:.1f}s dim={len(vectors[0])}")

    # Clear cached client if path reused across processes
    get_client.cache_clear()
    client = get_client(url="", path=args.qdrant_path)
    ensure_collection(
        client,
        args.collection,
        vector_size=len(vectors[0]) if vectors else VECTOR_SIZE,
        recreate=args.recreate,
    )
    n = upsert_chunks(client, texts, vectors, payloads, collection=args.collection)
    print(f"Upserted {n} points → {args.qdrant_path} / {args.collection}")

    manifest = {
        "source": str(args.input),
        "records": len(records),
        "chunks": len(chunks),
        "collection": args.collection,
        "embedding_model": DEFAULT_MODEL,
        "strategies": strategies,
        "note": "Bootstrap/local JSONL index; replace/extend with streamed MSMARCO-XI shards.",
    }
    Path("data/manifests").mkdir(parents=True, exist_ok=True)
    Path("data/manifests/mini_index.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("DONE")


if __name__ == "__main__":
    main()
