#!/usr/bin/env python3
"""Run the RAG pipeline over evaluation/queries.jsonl and write P50/P70/P100."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.orchestration.pipeline import run_pipeline
from evaluation.metrics import mrr, recall_at_k, summarize_latencies


def warmup() -> None:
    run_pipeline("What is the capital of India?", mode="fast")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, default=Path("evaluation/queries.jsonl"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--mode", default="fast", choices=["fast", "generative"])
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()

    queries = []
    with args.queries.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))
    if args.limit:
        queries = queries[: args.limit]

    print(f"Warming models ({len(queries)} queries, mode={args.mode})…")
    t_warm0 = time.perf_counter()
    warmup()
    warm_ms = (time.perf_counter() - t_warm0) * 1000
    print(f"warmup_ms={warm_ms:.1f}")

    results = []
    recalls = []
    mrrs = []
    refuse_ok = 0
    refuse_n = 0

    for i, item in enumerate(queries, start=1):
        q = item["query"]
        env = run_pipeline(q, mode=args.mode)  # type: ignore[arg-type]
        gold = item.get("query_id")
        sources = env.get("sources") or []
        rec = recall_at_k(sources, gold, k=5) if item.get("expect_answer") else None
        rr = mrr(sources, gold) if item.get("expect_answer") else None
        if rec is not None:
            recalls.append(rec)
        if rr is not None:
            mrrs.append(rr)
        if item.get("expect_answer") is False:
            refuse_n += 1
            if env.get("refused"):
                refuse_ok += 1
        row = {
            "i": i,
            "query": q,
            "split": item.get("split"),
            "refused": env.get("refused"),
            "grounded": env.get("grounded"),
            "answer": env.get("answer"),
            "latency_ms": env.get("latency_ms"),
            "recall@5": rec,
            "mrr": rr,
        }
        results.append(row)
        total = (env.get("latency_ms") or {}).get("total_rag")
        print(f"[{i}/{len(queries)}] {total} ms refused={env.get('refused')} {q[:60]}")

    lat_rows = [r["latency_ms"] for r in results if r.get("latency_ms")]
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "n": len(results),
        "mode": args.mode,
        "warmup_ms": round(warm_ms, 2),
        "latency": summarize_latencies(lat_rows),
        "recall@5": round(sum(recalls) / len(recalls), 4) if recalls else None,
        "mrr": round(sum(mrrs) / len(mrrs), 4) if mrrs else None,
        "adversarial_refusal_rate": round(refuse_ok / refuse_n, 4) if refuse_n else None,
        "note": "Warm RAG path after one warmup query. STT is excluded. Generative LLM is slower by design.",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = args.out_dir / f"benchmark_{stamp}.json"
    out.write_text(json.dumps({"summary": summary, "rows": results}, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
