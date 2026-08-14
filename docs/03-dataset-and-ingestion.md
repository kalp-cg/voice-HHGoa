# 03 — Dataset & Ingestion Strategy

## Source

- Dataset: [`ai4bharat/MSMARCO-XI`](https://huggingface.co/datasets/ai4bharat/MSMARCO-XI) (~55.6 GB)
- Indic MS MARCO translations (Gujarati, Hindi, Bengali, etc.)
- Fields (conceptually): `query`, `answer`, `passages`, English + translated passages, `query_id`, `query_type`, `source_lang`, `target_lang`, translation metadata

## Critical rule

**Do NOT download or materialize the full dataset into RAM.**

Wrong:

```python
dataset = load_dataset(...)
data = list(dataset)  # disaster on 16 GB RAM
```

Right: **streaming** + capped samples + progressive scale-up.

```python
from datasets import load_dataset

dataset = load_dataset(
    "ai4bharat/MSMARCO-XI",
    "hi",           # language config — confirm after inspection
    split="train",
    streaming=True,
)

for example in dataset.take(5):
    print(example)
```

## Scale phases (do not skip)

| Phase | Records | Goal |
|-------|---------|------|
| 1 | 10k–50k | Make the whole system work |
| 2 | 100k–500k | Test retrieval quality |
| 3 | 1M+ | Test scaling & latency |
| 4 | Largest practical | Final benchmark / demo |

## Do we need all 55.6 GB in the vector DB?

**Not necessarily.** Blind full embed can explode storage.

Example: 384-dim FP32 ≈ 1.5 KB/vector → 10M vectors ≈ 15.4 GB raw (before index overhead + metadata).

Mitigations to investigate:

- Deduplication
- Passage filtering
- Language-aware indexing
- Compact embeddings
- Quantization
- Qdrant storage configuration

## Ingestion pipeline (offline)

```text
MSMARCO-XI
  → STREAM BATCHES
  → CLEANING
  → DEDUPLICATION
  → LANGUAGE METADATA
  → MULTI-STRATEGY CHUNKING
  → EMBEDDINGS
  → QDRANT INDEX
```

## Storage policy

Keep raw / large artifacts **outside Git**:

```text
/mnt/data/msmarco-xi/   # or similar large disk
```

Repo contains code, configs, scripts, docs, **small** evaluation samples only.

Never commit: full dataset, embeddings, Qdrant storage, large parquet/jsonl dumps.
