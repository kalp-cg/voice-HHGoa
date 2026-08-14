# 04 — Chunking Strategies

Assignment requires **more than one naive fixed-size** strategy. Implement all of the following.

## Strategy A — Sentence chunks

Split passage into sentences; each sentence (or short group) is a chunk.

## Strategy B — Fixed / sliding window

Overlap windows over sentences, e.g. window=3, stride=1:

```text
chunk1 = s1,s2,s3
chunk2 = s2,s3,s4
chunk3 = s3,s4,s5
```

## Strategy C — Semantic chunks

Detect semantic boundaries (topic shifts), not only token counts. Group contiguous sentences that share a concept.

## Strategy D — Parent / child (priority)

```text
PARENT PASSAGE
  ├── Child 1
  ├── Child 2
  └── Child 3
```

- **Search** on child chunks (precision).
- **Return / prompt** with parent context when useful (recall + coherence).

## Strategy E — Metadata-aware

Every chunk carries payload such as:

```json
{
  "language": "hi",
  "source_lang": "eng_Latn",
  "target_lang": "hin_Deva",
  "query_id": 123,
  "query_type": "...",
  "chunk_type": "semantic",
  "parent_id": "...",
  "source": "MSMARCO-XI"
}
```

Retrieval can filter by language / chunk type / source.

## Design rule

**Inspect streamed samples first** (fields, passage length, duplicates, languages, query types). Only then lock chunker parameters. Do not design the final chunker blind.
