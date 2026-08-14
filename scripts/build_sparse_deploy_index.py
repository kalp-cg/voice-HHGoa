#!/usr/bin/env python3
"""Build a tiny BM25-only deploy index (no embeddings / Qdrant).

Used for Render Free (512 MB) where FastEmbed + ONNX OOM at runtime.
"""

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


def _align_record(rec: dict) -> dict:
    """Keep the passage that matches the record language so BM25 does not
    search English fragments for a Tamil / Hindi / Urdu query."""
    aligned = dict(rec)
    lang = str(aligned.get("language") or "")
    if lang and lang != "en":
        aligned["english_passages"] = []
    else:
        aligned["translated_passages"] = []
    return aligned


def _iter_local_jsonl(path: Path, limit: int) -> Iterator[dict]:
    with path.open(encoding="utf-8") as source:
        for i, line in enumerate(source):
            if i >= limit:
                break
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sparse-only deploy chunk index")
    parser.add_argument("--records", type=int, default=80)
    parser.add_argument("--max-chunks", type=int, default=250)
    parser.add_argument("--record-batch", type=int, default=32)
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=Path("data/samples/deploy_msmarco_multilingual.jsonl"),
    )
    parser.add_argument(
        "--bootstrap",
        type=Path,
        default=Path("data/samples/bootstrap_msmarco.jsonl"),
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Do not prepend bootstrap_msmarco.jsonl (use for multilingual samples).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qdrant_storage/deploy/chunks.jsonl"),
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Keep one copy of a passage per benchmark query. Different queries can
    # legitimately share a passage; collapsing those copies loses the hidden
    # source-query evidence used by retrieval and guardrails.
    seen_chunks: set[tuple[str, str]] = set()
    record_batch: list[dict] = [] if args.no_bootstrap else _load_bootstrap(args.bootstrap)
    bootstrap_n = len(record_batch)
    records_seen = bootstrap_n
    chunks_indexed = 0
    started = time.perf_counter()
    print(f"bootstrap_records={bootstrap_n}", flush=True)

    out_rows: list[dict] = []

    def flush() -> None:
        nonlocal chunks_indexed
        if not record_batch or chunks_indexed >= args.max_chunks:
            return
        query_by_id = {
            str(rec.get("query_id")): str(rec.get("query") or "").strip()
            for rec in record_batch
        }
        remaining = args.max_chunks - chunks_indexed
        total_expected = args.records + bootstrap_n
        proportional_cap = math.ceil(
            len(record_batch) * args.max_chunks / max(total_expected, 1)
        )
        chunks = compact_index_chunks(
            [_align_record(rec) for rec in record_batch],
            max_chunks=min(remaining, max(proportional_cap, 1)),
        )
        for ch in chunks:
            text = (ch.text or "").strip()
            if not text:
                continue
            th = text_hash(text)
            dedupe_key = (th, str(ch.query_id))
            if dedupe_key in seen_chunks:
                continue
            seen_chunks.add(dedupe_key)
            out_rows.append(
                {
                    "chunk_id": str(ch.chunk_id or f"c{chunks_indexed}"),
                    "text": text,
                    "parent_text": str(ch.parent_text or ""),
                    "chunk_type": str(ch.chunk_type or ""),
                    "language": str(ch.language or ""),
                    "passage_lang": str(ch.passage_lang or ""),
                    "query_id": ch.query_id,
                    "source_query": query_by_id.get(str(ch.query_id), ""),
                    # Search-only metadata: never returned as answer text.
                    "search_text": " ".join(
                        part
                        for part in (query_by_id.get(str(ch.query_id), ""), text)
                        if part
                    ),
                }
            )
            chunks_indexed += 1
            if chunks_indexed >= args.max_chunks:
                break
        record_batch.clear()

    source_seen = 0
    for row in _iter_local_jsonl(args.input_jsonl, args.records):
        source_seen += 1
        rec = clean_record(row)
        if not rec:
            continue
        record_batch.append(rec)
        records_seen += 1
        if len(record_batch) >= args.record_batch:
            flush()
            print(
                f"source_records={source_seen}/{args.records} "
                f"total_records={records_seen} chunks={chunks_indexed}/{args.max_chunks} "
                f"elapsed_s={time.perf_counter() - started:.1f}",
                flush=True,
            )
        if chunks_indexed >= args.max_chunks:
            break

    flush()

    with args.output.open("w", encoding="utf-8") as fh:
        for row in out_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "mode": "sparse",
        "input": str(args.input_jsonl),
        "output": str(args.output),
        "bootstrap_records": bootstrap_n,
        "source_records_seen": source_seen,
        "records_seen": records_seen,
        "chunks_indexed": chunks_indexed,
        "elapsed_s": round(time.perf_counter() - started, 2),
    }
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
