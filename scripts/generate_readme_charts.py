"""Stdlib SVG charts for the GitHub README (no matplotlib)."""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets"
BG = "#07140f"
CARD = "#0e241b"
INK = "#e8f6ee"
MUTED = "#8fb8a4"
GREEN = "#3dff8a"
TEAL = "#2ec4b6"
AMBER = "#ffb020"
RED = "#ff6b6b"
NAVY = "#7aa2ff"


def _svg(w: int, h: int, body: str, title: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
  <title>{title}</title>
  <rect width="{w}" height="{h}" rx="16" fill="{BG}"/>
  {body}
</svg>
'''


def why_not_55gb() -> None:
    # Log-ish visual: dump vs RAM vs host vs live index (GB)
    rows = [
        ("MSMARCO-XI full dump", 55.6, RED, "would not fit in RAM"),
        ("10M embeddings (example)", 15.4, AMBER, "vectors only, no index"),
        ("Laptop RAM", 16.0, NAVY, "hard ceiling"),
        ("Render Free RAM", 0.512, TEAL, "live host"),
        ("Live BM25 index", 0.052, GREEN, "what the demo loads"),
    ]
    w, h = 920, 420
    left, top, bar_h, gap = 280, 72, 44, 18
    max_w = 560
    # visual width uses log10(gb * 1000) so 0.052 still shows
    import math

    def vw(gb: float) -> float:
        return max(12.0, (math.log10(gb * 1000) / math.log10(55600)) * max_w)

    bars = []
    y = top
    for name, gb, color, note in rows:
        bw = vw(gb)
        label = f"{gb:g} GB"
        bars.append(
            f'''
  <text x="24" y="{y + 28}" fill="{INK}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="15">{name}</text>
  <rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="8" fill="{color}">
    <title>{name}: {gb} GB — {note}</title>
  </rect>
  <text x="{left + bw + 10:.1f}" y="{y + 28}" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">{label}</text>'''
        )
        y += bar_h + gap
    body = f'''
  <text x="24" y="36" fill="{GREEN}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="18" font-weight="700">Why we did not load 55.6 GB</text>
  <text x="24" y="56" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">Hover a bar. Scale is logarithmic so the live index is still visible.</text>
  {''.join(bars)}
  <text x="24" y="400" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">16 GB RAM cannot hold 55.6 GB. Render Free is 512 MB. We stream + cap instead.</text>
'''
    (OUT / "why-not-55gb.svg").write_text(_svg(w, h, body, "Why we did not load 55.6 GB"), encoding="utf-8")


def latency_stages() -> None:
    stages = [
        ("Embed", 11.1),
        ("Dense", 34.4),
        ("BM25", 34.1),
        ("Fusion", 0.1),
        ("Rerank", 0.9),
        ("Generate", 0.0),
        ("Total RAG", 93.2),
    ]
    w, h = 920, 380
    left, bottom, max_h = 70, 320, 240
    max_v = 100.0
    slot = 110
    bars = []
    for i, (name, val) in enumerate(stages):
        x = left + i * slot
        bh = max(4.0, (val / max_v) * max_h)
        y = bottom - bh
        color = GREEN if name == "Total RAG" else TEAL
        bars.append(
            f'''
  <rect x="{x}" y="{y:.1f}" width="72" height="{bh:.1f}" rx="8" fill="{color}">
    <title>{name} P50: {val} ms (STT excluded)</title>
  </rect>
  <text x="{x + 36}" y="{y - 8:.1f}" text-anchor="middle" fill="{INK}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">{val}</text>
  <text x="{x + 36}" y="{bottom + 22}" text-anchor="middle" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">{name}</text>'''
        )
    body = f'''
  <text x="24" y="36" fill="{GREEN}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="18" font-weight="700">Warm hybrid RAG — P50 milliseconds</text>
  <text x="24" y="56" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">N=190 queries · extractive path · STT is not in these bars · hover for detail</text>
  <line x1="50" y1="{bottom}" x2="880" y2="{bottom}" stroke="{CARD}" stroke-width="2"/>
  {''.join(bars)}
  <text x="24" y="362" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">P70 118.7 ms · P100 175.5 ms · assignment target RAG &lt; 200 ms</text>
'''
    (OUT / "latency-p50.svg").write_text(_svg(w, h, body, "Warm hybrid RAG P50 latency"), encoding="utf-8")


def percentiles() -> None:
    groups = [("P50", 93.2), ("P70", 118.7), ("P100", 175.5)]
    w, h = 920, 300
    left, bottom, max_h = 160, 240, 170
    max_v = 200.0
    bars = []
    for i, (name, val) in enumerate(groups):
        x = left + i * 220
        bh = (val / max_v) * max_h
        y = bottom - bh
        color = GREEN if val < 200 else AMBER
        bars.append(
            f'''
  <rect x="{x}" y="{y:.1f}" width="140" height="{bh:.1f}" rx="10" fill="{color}">
    <title>{name} RAG total {val} ms — under 200 ms target</title>
  </rect>
  <text x="{x + 70}" y="{y - 10:.1f}" text-anchor="middle" fill="{INK}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="20" font-weight="700">{val}</text>
  <text x="{x + 70}" y="{bottom + 28}" text-anchor="middle" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="16">{name}</text>'''
        )
    # target line
    ty = bottom - (200 / max_v) * max_h
    body = f'''
  <text x="24" y="36" fill="{GREEN}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="18" font-weight="700">RAG total vs 200 ms target</text>
  <text x="24" y="56" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">Local hybrid · 190 queries · speech-to-text excluded</text>
  <line x1="80" y1="{ty:.1f}" x2="860" y2="{ty:.1f}" stroke="{AMBER}" stroke-dasharray="6 6" stroke-width="2"/>
  <text x="868" y="{ty + 4:.1f}" fill="{AMBER}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">200 ms</text>
  {''.join(bars)}
'''
    (OUT / "latency-percentiles.svg").write_text(_svg(w, h, body, "RAG P50 P70 P100 vs 200ms"), encoding="utf-8")


def corpus() -> None:
    rows = [
        ("Live demo", 1965, 3432, GREEN),
        ("Local hybrid", 10005, 12000, TEAL),
        ("We do not index the dump", 0, 0, RED),
    ]
    w, h = 920, 340
    body_rows = []
    y = 90
    for name, rec, ch, color in rows:
        rec_w = 0 if rec == 0 else max(20, rec / 10005 * 480)
        ch_w = 0 if ch == 0 else max(20, ch / 12000 * 480)
        note = "not downloaded" if rec == 0 else f"{rec:,} records · {ch:,} chunks"
        body_rows.append(
            f'''
  <text x="24" y="{y + 18}" fill="{INK}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="15">{name}</text>
  <rect x="280" y="{y}" width="{rec_w:.1f}" height="16" rx="6" fill="{color}">
    <title>{name}: {note}</title>
  </rect>
  <rect x="280" y="{y + 22}" width="{ch_w:.1f}" height="16" rx="6" fill="{color}" opacity="0.55"/>
  <text x="780" y="{y + 22}" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">{note}</text>'''
        )
        y += 70
    body = f'''
  <text x="24" y="36" fill="{GREEN}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="18" font-weight="700">What is actually indexed</text>
  <text x="24" y="56" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">Solid = records · faded = chunks · hover bars</text>
  {''.join(body_rows)}
  <text x="24" y="318" fill="{MUTED}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">Live: 15 languages, BM25-only. Local: dense + BM25 hybrid, mostly Hindi 10k sample.</text>
'''
    (OUT / "corpus-indexed.svg").write_text(_svg(w, h, body, "Indexed corpus vs dump"), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    why_not_55gb()
    latency_stages()
    percentiles()
    corpus()
    print("wrote", list(OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
