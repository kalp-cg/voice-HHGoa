#!/usr/bin/env python3
"""Evaluate every query in the balanced sparse deployment sample."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=Path,
        default=ROOT / "data/samples/deploy_msmarco_multilingual.jsonl",
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=ROOT / "qdrant_storage/deploy-eval",
    )
    args = parser.parse_args()

    os.environ["QDRANT_PATH"] = str(args.index)
    os.environ["RETRIEVAL_MODE"] = "sparse"
    os.environ["SKIP_STARTUP_WARMUP"] = "1"

    from backend.orchestration.pipeline import run_pipeline

    rows = [
        json.loads(line)
        for line in args.sample.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_language: dict[str, Counter] = defaultdict(Counter)
    failures: list[dict[str, str | None]] = []

    for row in rows:
        expected = str(row.get("language") or "")
        result = run_pipeline(str(row.get("query") or ""), mode="fast")
        top = (result.get("sources") or [{}])[0]
        actual = str(top.get("language") or "")
        stats = by_language[expected]
        stats["total"] += 1
        if actual == expected:
            stats["same_language"] += 1
        if result.get("grounded") and not result.get("refused"):
            stats["answered"] += 1
        else:
            failures.append(
                {
                    "language": expected,
                    "query": str(row.get("query") or ""),
                    "reason": result.get("refusal_reason"),
                    "top_language": actual or None,
                }
            )

    totals = sum(by_language.values(), Counter())
    total = totals["total"]
    summary = {
        "sample": str(args.sample),
        "index": str(args.index),
        "records": total,
        "answered": totals["answered"],
        "answer_rate": round(totals["answered"] / total, 4) if total else 0.0,
        "same_language_top_hit": totals["same_language"],
        "same_language_rate": (
            round(totals["same_language"] / total, 4) if total else 0.0
        ),
        "languages": {
            lang: dict(stats) for lang, stats in sorted(by_language.items())
        },
        "failures": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
