#!/usr/bin/env python3
"""Rebuild a practical mini-index from bootstrap + 10k Hindi JSONL."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.chunking import compact_index_chunks
from ingestion.clean import clean_record
from ingestion.embed import DEFAULT_MODEL, embed_texts
from retrieval.qdrant import (
    COLLECTION,
    VECTOR_SIZE,
    ensure_collection,
    get_client,
    upsert_chunks,
)


def load_jsonl(path: Path, limit: int | None = None) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = clean_record(json.loads(line))
            if rec:
                rows.append(rec)
            if limit and len(rows) >= limit:
                break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=Path, default=Path("data/samples/bootstrap_msmarco.jsonl"))
    parser.add_argument("--msmarco", type=Path, default=Path("data/processed/msmarco_xi_hi_10k.jsonl"))
    parser.add_argument("--qdrant-path", default="qdrant_storage/local")
    parser.add_argument("--max-chunks", type=int, default=16_000)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    if not args.bootstrap.exists():
        raise SystemExit(f"missing bootstrap sample: {args.bootstrap}")
    if not args.msmarco.exists():
        raise SystemExit(
            f"missing MSMARCO sample: {args.msmarco}\n"
            "Export it first, or run:\n"
            "  python scripts/build_streaming_index.py --input-jsonl <jsonl> --recreate"
        )

    records = load_jsonl(args.bootstrap) + load_jsonl(args.msmarco)
    print(f"records={len(records)}")
    chunks = compact_index_chunks(records, max_chunks=args.max_chunks)
    print(f"chunks={len(chunks)}")
    texts = [c.text for c in chunks]
    payloads = [c.payload() for c in chunks]

    t0 = time.perf_counter()
    vectors = embed_texts(texts, batch_size=64)
    print(f"embed_s={time.perf_counter()-t0:.1f} dim={len(vectors[0]) if vectors else 0}")

    get_client.cache_clear()
    client = get_client(url="", path=args.qdrant_path)
    ensure_collection(
        client,
        COLLECTION,
        vector_size=len(vectors[0]) if vectors else VECTOR_SIZE,
        recreate=args.recreate,
    )
    n = upsert_chunks(client, texts, vectors, payloads, collection=COLLECTION)
    print(f"upserted={n}")

    manifest = {
        "records": len(records),
        "chunks": len(chunks),
        "collection": COLLECTION,
        "embedding_model": DEFAULT_MODEL,
        "bootstrap": str(args.bootstrap),
        "msmarco": str(args.msmarco),
        "note": "compact unique-text chunks covering all records",
    }
    Path("data/manifests").mkdir(parents=True, exist_ok=True)
    Path("data/manifests/mini_index.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("DONE")


if __name__ == "__main__":
    main()
