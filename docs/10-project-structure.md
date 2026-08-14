# 10 — Project Structure

Target layout (folder may be named `voice-HHgoa` / `voice-rag-goa`):

```text
voice-rag-goa/
├── README.md
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── docs/                          # this documentation set
│
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── routes_voice.py
│   │   ├── routes_query.py
│   │   └── routes_health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── telemetry.py
│   ├── stt/
│   │   └── elevenlabs_client.py
│   ├── retrieval/
│   │   ├── dense.py
│   │   ├── sparse.py
│   │   ├── hybrid.py
│   │   └── reranker.py
│   ├── generation/
│   │   ├── llm.py
│   │   └── prompts.py
│   ├── guardrails/
│   │   ├── relevance.py
│   │   ├── grounding.py
│   │   └── safety.py
│   └── orchestration/
│       └── pipeline.py
│
├── ingestion/
│   ├── inspect_dataset.py
│   ├── stream_dataset.py
│   ├── clean.py
│   ├── deduplicate.py
│   ├── chunking/
│   │   ├── sentence.py
│   │   ├── sliding_window.py
│   │   ├── semantic.py
│   │   └── parent_child.py
│   ├── embed.py
│   └── index.py
│
├── retrieval/
│   ├── qdrant.py
│   └── schemas.py
│
├── evaluation/
│   ├── queries.jsonl
│   ├── benchmark.py
│   ├── metrics.py
│   └── results/
│
├── frontend/
│   ├── index.html
│   └── src/
│
├── scripts/
│   ├── setup.sh
│   ├── download_sample.py
│   ├── build_index.py
│   └── benchmark.sh
│
├── data/
│   ├── samples/
│   ├── processed/
│   └── manifests/
│
└── qdrant_storage/                # gitignored
```

**Do not commit:** dataset dumps, embeddings, Qdrant storage, secrets.
