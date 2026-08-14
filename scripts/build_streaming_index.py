#!/usr/bin/env python3
"""Build a capped MSMARCO-XI index directly from a streamed Hub shard."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.chunking import compact_index_chunks
from ingestion.clean import clean_record
from ingestion.deduplicate import text_hash
from ingestion.embed import DEFAULT_MODEL, embed_texts
from ingestion.stream_dataset import DATASET_ID, iter_examples, normalize_record
from retrieval.qdrant import COLLECTION, VECTOR_SIZE, ensure_collection, get_client, upsert_chunks


def _load_bootstrap(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = clean_record(json.loads(line))
        if rec:
            rows.append(rec)
    return rows


def _iter_local_jsonl(path: Path, limit: int) -> Iterator[dict]:
    with path.open(encoding="utf-8") as source:
        for i, line in enumerate(source):
            if i >= limit:
                break
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stream, chunk, embed, and index a capped MSMARCO-XI sample"
    )
    parser.add_argument("--language", default="hi")
    parser.add_argument("--split", default="train", choices=["train", "validation"])
    parser.add_argument("--records", type=int, default=50_000)
    parser.add_argument("--max-chunks", type=int, default=60_000)
    parser.add_argument("--record-batch", type=int, default=256)
    parser.add_argument("--embed-batch", type=int, default=64)
    parser.add_argument("--qdrant-path", default="qdrant_storage/local")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        help="Use an existing normalized MSMARCO-XI JSONL instead of the Hub",
    )
    parser.add_argument(
        "--bootstrap",
        type=Path,
        default=Path("data/samples/bootstrap_msmarco.jsonl"),
    )
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    if args.records < 1 or args.max_chunks < 1:
        parser.error("--records and --max-chunks must be positive")

    client = get_client(url="", path=args.qdrant_path)
    ensure_collection(
        client,
        COLLECTION,
        vector_size=VECTOR_SIZE,
        recreate=args.recreate,
    )

    seen_texts: set[str] = set()
    record_batch: list[dict] = _load_bootstrap(args.bootstrap)
    bootstrap_n = len(record_batch)
    records_seen = bootstrap_n
    chunks_indexed = 0
    started = time.perf_counter()
    print(f"bootstrap_records={bootstrap_n}", flush=True)

    def flush() -> None:
        nonlocal chunks_indexed
        if not record_batch or chunks_indexed >= args.max_chunks:
            return
        remaining = args.max_chunks - chunks_indexed
        total_expected = args.records + bootstrap_n
        proportional_cap = math.ceil(
            len(record_batch) * args.max_chunks / total_expected
        )
        chunks = compact_index_chunks(
            record_batch,
            max_chunks=min(remaining, max(len(record_batch), proportional_cap)),
        )
        unique = []
        for chunk in chunks:
            digest = text_hash(chunk.text)
            if digest in seen_texts:
                continue
            seen_texts.add(digest)
            unique.append(chunk)
        record_batch.clear()
        if not unique:
            return
        texts = [chunk.text for chunk in unique]
        vectors = embed_texts(texts, batch_size=args.embed_batch)
        payloads = [chunk.payload() for chunk in unique]
        chunks_indexed += upsert_chunks(
            client,
            texts,
            vectors,
            payloads,
            collection=COLLECTION,
        )
        elapsed = time.perf_counter() - started
        print(
            f"source_records={source_records_seen}/{args.records} "
            f"total_records={records_seen} "
            f"chunks={chunks_indexed}/{args.max_chunks} elapsed_s={elapsed:.1f}",
            flush=True,
        )

    if args.input_jsonl:
        rows = _iter_local_jsonl(args.input_jsonl, args.records)
    else:
        rows = (
            normalize_record(row, args.language)
            for row in iter_examples(args.language, args.split, args.records)
        )

    source_records_seen = 0
    for normalized in rows:
        source_records_seen += 1
        records_seen += 1
        cleaned = clean_record(normalized)
        if cleaned:
            record_batch.append(cleaned)
        if len(record_batch) >= args.record_batch:
            flush()
        if chunks_indexed >= args.max_chunks:
            break
    flush()

    manifest = {
        "dataset": DATASET_ID,
        "language": args.language,
        "split": args.split,
        "input": str(args.input_jsonl) if args.input_jsonl else "huggingface_stream",
        "record_cap": args.records,
        "bootstrap_records": bootstrap_n,
        "source_records_seen": source_records_seen,
        "records_seen": records_seen,
        "chunk_cap": args.max_chunks,
        "chunks_indexed": chunks_indexed,
        "collection": COLLECTION,
        "embedding_model": DEFAULT_MODEL,
        "streaming": args.input_jsonl is None,
        "elapsed_s": round(time.perf_counter() - started, 2),
    }
    manifest_dir = Path("data/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    out = manifest_dir / f"stream_index_{args.language}_{args.split}_{records_seen}.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
