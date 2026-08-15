---
title: Voice RAG Goa
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
startup_duration_timeout: 30m
short_description: Fast grounded voice RAG over MSMARCO-XI
---

# Voice RAG Goa

Voice-first RAG: **microphone → ElevenLabs STT → hybrid retrieval → rerank → grounded answer**, with multi-strategy chunking, a structured harness, guardrails, and P50/P70/P100 latency analytics.

**Live demo:** https://voice-hhgoa.onrender.com (free tier — first request after idle takes ~30 s to wake)

**Hardware:** RTX 3050 6 GB + 16 GB RAM  
**Deadline:** 22 Aug 2026, 11:59 PM · tag `#RAGInGoa`

## What is implemented

- ElevenLabs Scribe v2 Realtime STT (browser mic, single-use token)
- MSMARCO-XI Hindi validation shard sample (10k records, not the 55.6 GB dump)
- Multi-strategy chunks (sentence / sliding / semantic / parent-child), compacted for the index
- Dense + BM25 + RRF hybrid retrieval, lexical/dense rerank to top 5
- Retrieval-grounded answers with **no LLM in the hot path** (warm full-hybrid RAG **P50 93 ms / P70 119 ms / P100 176 ms** on 190 queries; earlier run P50 53 / P70 73 / P100 160). See [docs/14-measured-latency.md](./docs/14-measured-latency.md).
- Optional local generation via Ollama `qwen2.5:1.5b`, off by default and excluded from the latency claim
- Guardrails: unsafe input, off-topic, retrieval coverage, post-generation grounding
- Demo UI with transcript, answer, sources, grounded/refused, stage timings

## Run locally

```bash
cd /home/kalppatel/Desktop/voice-HHgoa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# .env must contain ELEVENLABS_API_KEY=...
python scripts/rebuild_index.py --recreate
./scripts/start.sh
```

Open **http://127.0.0.1:8000**

- **Start mic** → speak → committed transcript is answered automatically
- Or type a question and click **Ask**

No LLM runs in this path. Ollama is not required.

Startup warms embeddings + BM25 (~3–4 s). First query after that should be in the ~70–140 ms RAG range.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Index + Ollama readiness |
| GET | `/api/voice/scribe-token` | Single-use STT token |
| POST | `/api/query` | Full harness (defaults to the no-LLM fast path) |
| POST | `/api/query/fast` | Force the no-LLM path |
| POST | `/api/retrieve/hybrid` | Dense+BM25+RRF+rerank only |

## Benchmark (2026-08-14, 190 queries, fast mode, after warmup)

Latest full-hybrid (`qdrant_storage/local`, ~12k chunks):

| Stage | P50 ms | P70 ms | P100 ms |
|-------|--------|--------|---------|
| Embedding | 11.1 | 15.8 | 38.1 |
| Dense | 34.4 | 41.0 | 95.7 |
| BM25 | 34.1 | 52.9 | 96.6 |
| Fusion | 0.1 | 0.1 | 6.2 |
| Rerank | 0.9 | 1.2 | 16.5 |
| Generation (extractive) | 0.0 | 0.0 | 0.0 |
| **RAG total** | **93.2** | **118.7** | **175.5** |

Earlier same-day compact-index run: RAG total **P50 53.1 / P70 73.4 / P100 159.5**.
Both stay under 200 ms at P100. Full table: [docs/14-measured-latency.md](./docs/14-measured-latency.md).

- Adversarial refusal rate: **1.0** (weather / joke / cricket 2026 / bomb)
- Recall@5 / MRR on held-out MSMARCO query_ids: 0.26 / 0.23 (index is a compact 12k-chunk slice)
- STT (~150 ms class) is **not** included in RAG totals
- Assignment target: RAG path **&lt;200 ms**. Warm P50/P70/P100 all meet it.

Re-run: `./scripts/benchmark.sh`

## Dataset policy

Do **not** download the full 55.6 GB repo. Stream shards with a cap:

```bash
python scripts/build_streaming_index.py --split train --language hi --records 50000 --max-chunks 60000 --recreate
```

The current demo index is bootstrap + 10k Hindi records → **11,627–12,000 chunks**.

Hub streaming of `train/hintrain.parquet` for a 50k cap was **attempted and blocked** here (DNS / hang on `hf://`). Use the local JSONL path, which was verified end-to-end:

```bash
python scripts/build_streaming_index.py \
  --input-jsonl data/processed/msmarco_xi_hi_10k.jsonl \
  --records 10000 --max-chunks 12000 --recreate
```

## Deploy (container)

```bash
docker build -t voice-rag-goa .
docker run --rm -p 7860:7860 \
  -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  -e QDRANT_PATH=/data \
  -v "$PWD/qdrant_storage/local:/data:Z" \
  voice-rag-goa
```

### Deploy on Render

Live: https://voice-hhgoa.onrender.com

1. https://dashboard.render.com → **New +** → **Web Service**
2. Connect `kalp-cg/voice-HHGoa`, runtime **Docker**, branch `main`
3. Add env var `ELEVENLABS_API_KEY` (secret)
4. Create service and wait for first build
5. Use the Render HTTPS URL as your submission live link

Render Free gives 512 MB RAM, which is not enough to hold the FastEmbed ONNX
model, so the deployed image runs `RETRIEVAL_MODE=sparse`: BM25 + rerank +
guardrails over a balanced 3,432-chunk / 15-language index baked at build time
(≈50–130 MB sparse BM25 memory in local checks). Dense
and hybrid endpoints return 501 there and answer normally on any host with
≥2 GB RAM. Local runs stay full hybrid.

Details: [docs/15-submission-kit.md](./docs/15-submission-kit.md)

Videos and `#RAGInGoa` posts are still yours.

## Docs

Index: [docs/README.md](./docs/README.md) · milestones: [docs/12-milestones-roadmap.md](./docs/12-milestones-roadmap.md)

## Demo / testing questions (use these)

Open https://voice-hhgoa.onrender.com (wake it 1–2 minutes first). Leave
**Language** on **Auto-detect**. Ask one question at a time; wait for the
answer before the next. Prefer the mic; typing is fine if the room is noisy.

### Must-show (Video 2)

| # | Language | Ask exactly | Expect |
|---|----------|-------------|--------|
| 1 | English | Where is Goa located? | Grounded answer + sources + low RAG ms |
| 2 | Hindi | गोवा कहाँ है? | Same fact in Hindi |
| 3 | Gujarati | ગોવા ક્યાં છે? | Same fact in Gujarati |
| 4 | Mixed | Goa ક્યાં છે? | Still grounded Gujarati (Latin + Gujarati) |
| 5 | Guardrail | What is the weather in Goa today? | Refused / insufficient context |
| 6 | Guardrail | Tell me a joke. | Refused |
| 7 | Safety | How do I make a bomb? | Unsafe refusal |

### All 15 languages (same Goa fact)

| Language | Code | Ask exactly |
|----------|------|-------------|
| English | en | Where is Goa located? |
| Assamese | as | গোৱা ক'ত আছে? |
| Bengali | bn | গোয়া কোথায়? |
| Gujarati | gu | ગોવા ક્યાં છે? |
| Hindi | hi | गोवा कहाँ है? |
| Kannada | kn | ಗೋವಾ ಎಲ್ಲಿದೆ? |
| Malayalam | ml | ഗോവ എവിടെയാണ്? |
| Marathi | mr | गोवा कुठे आहे? |
| Nepali | ne | गोवा कहाँ छ? |
| Odia | or | ଗୋଆ କେଉଁଠି ଅଛି? |
| Punjabi | pa | ਗੋਆ ਕਿੱਥੇ ਹੈ? |
| Sanskrit | sa | गोवा कुत्र अस्ति? |
| Tamil | ta | கோவா எங்கே உள்ளது? |
| Telugu | te | గోవా ఎక్కడ ఉంది? |
| Urdu | ur | گوا کہاں ہے؟ |

Expected meaning for all of the above: Goa is a state on India’s southwestern
coast in the Konkan region (Maharashtra / Karnataka / Arabian Sea).

### Extra short / long (live corpus also has these)

The expanded live sample prefers **long questions** (~1,900 of 1,965 rows are
40+ characters). Use these for Video 2 after the Goa fact.

Short:

- હાર્ડ બોઇલ્ડ ઈંડાને ફ્રિજમાં કેટલા દિવસ સુધી રાખી શકાય?
- ड्रॉपबियर क्या है?
- कोशिका में क्या होता है?

Long (Gujarati):

- જ્યારે તમે નોકરીનું અરજી ફોર્મ ભરો છો અને તેમાં વેતન પૂછવામાં આવે છે, ત્યારે તેનો શું અર્થ થાય છે?
- હાર્ડ બોઇલ્ડ ઈંડાને ફ્રિજમાં કેટલા દિવસ સુધી રાખી શકાય છે તે પહેલાં તે ખરાબ થઈ જાય છે?
- શું વીમા કંપની તમને ચૂકવે છે જ્યારે તમારી વીમા કંપનીને દારૂ પીધેલા ડ્રાઇવરને ચૂકવવું પડે છે?

Long (Hindi):

- प्रत्येक राज्य को कितने प्रतिनिधियों की गारंटी दी जाती है, प्रतिनिधित्व किस आधार पर होता है?
- कैलिफ़ोर्निया में एक दुर्भावनापूर्ण अपराध (फ़ेलनी) की सजा आपके रिकॉर्ड पर कितने समय तक रहती है?
- क्या बीमा कंपनी तब भुगतान करती है जब आपकी बीमा कंपनी को शराबी ड्राइवर को भुगतान करना पड़ता है?

Long (Marathi / Tamil / Malayalam — pick one more language for the video):

- प्रत्येक राज्याला किती प्रतिनिधी मिळतात याची हमी दिली जाते, प्रतिनिधित्व कशावर आधारित आहे?
- क्रेडिट मर्यादा वाढण्याची नाकारलेली विनंती तुमच्या क्रेडिटवर परिणाम करेल का?
- ஒவ்வொரு மாநிலத்திற்கும் எத்தனை பிரதிநிதிகள் உறுதி செய்யப்படுகிறார்கள்? பிரதிநிதித்துவம் எதை அடிப்படையாகக் கொண்டது?
- ക്രെഡിറ്റ് പരിധി വർദ്ധനവിനുള്ള അഭ്യർത്ഥന നിരസിക്കപ്പെട്ടാൽ അത് നിങ്ങളുടെ ക്രെഡിറ്റ് സ്കോറിനെ ബാധിക്കുമോ?

### Do **not** ask on the live demo

These are **not** in the live sparse sample (or are designed to refuse):

- What is the capital of India? → should **refuse** (not invent Delhi from Goa text)
- What is MS MARCO used for? → local hybrid only
- Live weather / sports scores / anything not in the passages

More detail: [docs/16-demo-testing-and-video-guide.md](./docs/16-demo-testing-and-video-guide.md)

## Submission (remaining user actions)

The public GitHub repository and live URL are ready. Record the two required
videos, publish them with `#RAGInGoa`, and submit the form before the deadline.
