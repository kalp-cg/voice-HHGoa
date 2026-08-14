#!/usr/bin/env python3
"""Ask the demo question in every indexed language with no language hint.

Verifies that script-based detection alone (no dropdown, no STT language code)
routes each query to a passage in the same language.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INDEX = os.environ.get("CHECK_INDEX", "qdrant_storage/deploy-lang")
os.environ["QDRANT_PATH"] = INDEX
os.environ["RETRIEVAL_MODE"] = "sparse"

from backend.core.languages import detect_languages  # noqa: E402
from backend.orchestration.pipeline import run_pipeline  # noqa: E402


def main() -> int:
    sample = ROOT / "data/samples/deploy_msmarco_multilingual.jsonl"
    rows = [json.loads(l) for l in sample.read_text(encoding="utf-8").splitlines() if l.strip()]
    queries: dict[str, str] = {}
    for row in rows:
        # Curated demo rows are first; do not replace them with later benchmark
        # rows now that the deployed sample contains more than one per language.
        queries.setdefault(row.get("language") or "?", row.get("query") or "")

    failures = []
    for lang, query in sorted(queries.items()):
        result = run_pipeline(query, mode="fast")
        top = (result.get("sources") or [{}])[0]
        got = (top.get("language") or "?").strip()
        ok = bool(result.get("grounded")) and not result.get("refused") and got == lang
        if not ok:
            failures.append(lang)
        print(
            f"{'ok ' if ok else 'FAIL'} {lang:>3} -> hit={got:>3} "
            f"scripts={sorted(detect_languages(query))} "
            f"grounded={result.get('grounded')} refused={result.get('refusal_reason') or '-'} "
            f"| {query[:44]}"
        )

    print(f"\n{len(queries) - len(failures)}/{len(queries)} languages resolved without a hint")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
