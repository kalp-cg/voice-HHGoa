"""Per-request timers and percentile helpers."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


class StageTimer:
    def __init__(self) -> None:
        self.stages: dict[str, float] = {}
        self._started = time.perf_counter()

    @contextmanager
    def track(self, name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.add(name, (time.perf_counter() - t0) * 1000)

    def add(self, name: str, ms: float) -> None:
        self.stages[name] = round(self.stages.get(name, 0.0) + float(ms), 2)

    def total(self) -> float:
        return round((time.perf_counter() - self._started) * 1000, 2)

    def as_dict(self) -> dict[str, float]:
        out = dict(self.stages)
        out["total_rag"] = self.total()
        return out


def percentiles(values: list[float], ps: tuple[int, ...] = (50, 70, 100)) -> dict[str, float]:
    if not values:
        return {f"p{p}": 0.0 for p in ps}
    ordered = sorted(values)
    n = len(ordered)
    out: dict[str, float] = {}
    for p in ps:
        if p >= 100:
            out[f"p{p}"] = round(ordered[-1], 2)
            continue
        idx = min(n - 1, max(0, int(round((p / 100) * (n - 1)))))
        out[f"p{p}"] = round(ordered[idx], 2)
    return out
