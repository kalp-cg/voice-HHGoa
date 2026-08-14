#!/usr/bin/env python3
"""Export a capped number of rows from a local MSMARCO-XI parquet shard to JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.clean import clean_record
from ingestion.stream_dataset import normalize_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parquet",
        type=Path,
        default=Path("data/raw/msmarco-xi/validation/hinval.parquet"),
    )
    parser.add_argument("--language", default="hi")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/msmarco_xi_hi_10k.jsonl"),
    )
    args = parser.parse_args()

    if not args.parquet.exists():
        raise SystemExit(f"Missing parquet: {args.parquet}")

    pf = pq.ParquetFile(args.parquet)
    print(f"num_row_groups={pf.metadata.num_row_groups} rows≈{pf.metadata.num_rows}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    scanned = 0
    with args.out.open("w", encoding="utf-8") as out:
        for rg in range(pf.metadata.num_row_groups):
            table = pf.read_row_group(rg)
            for batch in table.to_batches(max_chunksize=256):
                for row in batch.to_pylist():
                    scanned += 1
                    rec = clean_record(normalize_record(row, args.language))
                    if not rec:
                        continue
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    kept += 1
                    if kept >= args.limit:
                        print(f"Wrote {kept} clean / scanned {scanned} → {args.out}")
                        return
            print(f"row_group={rg} scanned={scanned} kept={kept}")
    print(f"Wrote {kept} clean / scanned {scanned} → {args.out}")


if __name__ == "__main__":
    main()
