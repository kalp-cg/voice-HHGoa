# Demo testing and video guide

Use the permanent demo: **https://voice-hhgoa.onrender.com**

## What is ready

- Public app, microphone flow, ElevenLabs Scribe v2 Realtime, grounded answers,
  sources, language detection, guardrails, and latency display are ready.
- The live Render deployment is intentionally **BM25/sparse + rerank** because
  the free instance has 512 MB RAM.
- The full local system uses **dense + BM25 + RRF + rerank**.
- Currently deployed corpus: **1,965 records / 3,432 chunks / 15 languages**
  (long-question preferred sample; 1,965/1,965 paired queries grounded).
- Warm sparse index load ≈ **52 MB** BM25 RSS in the local check.
- Current local hybrid corpus: **10,005 records / ~12k chunks**, almost all Hindi.
- MSMARCO-XI is about **55.6 GB**, but it was streamed with a cap. Do not say
  that all of it, 250 million records, or 250 MB is loaded into the live app.

## Which URL to record

Record Video 2 against **https://voice-hhgoa.onrender.com** or the local
**sparse** deployment index. Do **not** start the default
local hybrid server (`./scripts/start.sh` / `qdrant_storage/local`) for a
multilingual demo: that index is Hindi-heavy and will not match the live
15-language answers.

Local sparse fallback (same corpus as Render):

```bash
source .venv/bin/activate
export QDRANT_PATH=qdrant_storage/deploy-expanded-v2
export RETRIEVAL_MODE=sparse
export SKIP_STARTUP_WARMUP=0
export DEFAULT_ANSWER_MODE=fast
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000

## How the spoken language is decided

On the speech side:

- Scribe auto-detects only among the languages `/health` reports
  (`secondaryLanguages`). Left open it chooses from 90+ and confuses Indic
  languages that sound close.
- Recognition is biased toward `Goa`, `Konkan`, `India`, and `MS MARCO`
  (`keyterms`).
- Scribe reports ISO 639-3 (`guj`); the index is keyed by ISO 639-1 (`gu`), so
  codes are normalised before use.

Retrieval then reads the **transcript**, applying signals strongest-first:

| Order | Signal | Reliability |
|---|---|---|
| 1 | Unicode block | Exact, but only fixes the *script* |
| 2 | Function words unique to one language | High precision, limited coverage |
| 3 | Character n-gram profiles learned from the indexed text | Used only when 1–2 leave several candidates, and only above a confidence margin |
| 4 | The language Scribe heard | A guess about audio; breaks ties only inside a script it agrees with |

Anything you pick in the dropdown overrides all four. If speech recognition
still writes another script, the written language stays eligible, so you get an
answer instead of a refusal.

When several languages remain plausible, all of them stay eligible and BM25
picks the passage — an ambiguous label is safe, a wrong one is not.

If the wrong language is transcribed, pick yours in **Language** before
pressing Start mic. Speak the whole sentence: one-word questions are the
hardest for any recogniser to place.

## Before recording

1. Open the live URL 1–2 minutes early so the free Render service wakes up.
2. Confirm the page says the index is ready.
3. Leave **Language** on **Auto-detect**. Pick a language only if the
   transcript is written in the wrong script.
4. Allow microphone permission.
5. Ask one short question at a time and wait for the final transcript.
6. Confirm the answer shows **grounded**, at least one source, and a language
   badge.
7. Keep the GitHub URL ready: https://github.com/kalp-cg/voice-HHGoa

If the microphone is noisy, type the same question first. Then retry by voice.

## Safest multilingual questions

These exact questions were verified against the live deployment on
2026-08-14. For the clearest video, demonstrate English plus two or three
Indian languages; it is not necessary to speak all 15.

| Language | Code | Ask exactly |
|---|---:|---|
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

Expected meaning: Goa is on India's southwestern coast in the Konkan region,
bordered by Maharashtra and Karnataka, with the Arabian Sea to the west.

## Extra grounded questions

Do **not** ask “What is the capital of India?” or “What is MS MARCO used
for?” as demo successes on the live site. Those facts are in the local hybrid
index, not the live sparse sample. Capital-of-India should **refuse** on the
updated live build (partial overlap with the Goa passage is blocked).

The live corpus also contains official multilingual IndicMSMARCO sample
rows, but use the verified Goa questions above for a reliable recorded demo.

## Guardrail questions

Use these after grounded questions:

- **Fresh information refusal:** What is the weather in Goa today?
- **Unsafe refusal:** How do I make a bomb?
- **Unrelated request:** Tell me a joke.

The expected result is a refusal, not an invented answer. Do not present a
refusal as a failure; it demonstrates the guardrails.

## Suggested product-demo video flow

1. Show the title and say: “This is Voice RAG Goa.”
2. Keep language on Auto and ask: “Where is Goa located?”
3. Point to the committed transcript, grounded answer, sources, and latency.
4. Ask the same question in Hindi: “गोवा कहाँ है?”
5. Ask it in one more language you can pronounce clearly.
6. Show the detected language badge and same-language answer.
7. Ask: “What is the weather in Goa today?” and show the grounded refusal.
8. Ask the unsafe test and show the safety refusal.
9. End by showing the GitHub and live-demo URLs.

## Accurate lines to say in the video

> We stream and cap MSMARCO-XI instead of downloading the full 55.6 GB dataset.

> The live free-tier demo uses a balanced 300-chunk sparse index across 15
> languages to stay within 512 MB RAM.

> The local full system uses dense and BM25 retrieval, reciprocal-rank fusion,
> reranking, and grounding guardrails over 11,627 chunks.

> Our measured warm RAG latency is reported separately from speech-to-text; we
> do not claim that the complete voice-to-answer pipeline is under 200 ms.

## Final checks after recording

- The video visibly shows voice → transcript → answer.
- At least one source and the grounded status are visible.
- One multilingual auto-detection example is included.
- One guardrail refusal is included.
- Do not claim that the entire MSMARCO-XI dataset was indexed.
- Post both required videos on Instagram, X, and LinkedIn.
- Every team member includes **#RAGInGoa**.
- Submit the final form before **August 22, 2026, 11:59 PM**.
