# 06 — Voice / STT (ElevenLabs)

## Role

ElevenLabs is the **voice layer only** (Milestone 1 freeze after it works).

```text
Microphone
  → Scribe v2 Realtime
  → partial transcript
  → committed transcript
```

## Docs

- [Client-side streaming STT](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/client-side-streaming)
- [Scribe v2 Realtime intro](https://elevenlabs.io/blog/introducing-scribe-v2-realtime) (~150 ms STT latency advertised, excl. app/network)

## Honesty on latency

Scribe alone is on the order of ~150 ms. **Do not claim** full microphone → final answer <200 ms as guaranteed.

Measure:

- STT separately
- RAG total (embed → retrieve → rerank → LLM → guardrail)
- Full voice pipeline end-to-end

Report all three.

## Milestone 1 success criteria

Speak: *"What is the capital of India?"*  
Observe transcript in browser/terminal.

Then **freeze STT** and move to dataset inspection. Do not keep churning STT while building RAG.

## Language handling (no dropdown)

The demo never asks which language you speak, matching how ChatGPT and similar
tools behave. Three signals, in increasing order of trust:

1. **Scribe detection.** `Scribe.connect` is opened with
   `includeLanguageDetection: true` (needs `@elevenlabs/client` ≥ 1.17.0; older
   versions never send `include_language_detection`, so `language_code` always
   came back `null`). The detected code arrives on
   `committed_transcript_with_timestamps` and is sent to `/api/query` as
   `language_hint`.
2. **Script of the transcript.** `backend/core/languages.py` maps Unicode blocks
   to languages. This is the primary signal because it describes the text that
   will actually be retrieved, so it cannot disagree with it.
3. **Function words.** Where several languages share a script (Devanagari →
   Hindi / Marathi / Nepali / Sanskrit; Bengali → Bengali / Assamese),
   interrogatives and copulas such as `कहाँ` / `कुठे` / `छ` / `अस्ति` pick one,
   as do Assamese-only characters `ৰ` and `ৱ`.

The hint is only honoured when it agrees with the script, so a misdetected
language cannot send retrieval to the wrong corpus. Short spoken questions are
exactly where acoustic detection is weakest — Whisper-class models detect from
the first seconds of audio — and this is why detection alone is not trusted.

`scripts/check_auto_language.py` asks the demo question in all 15 indexed
languages with no hint at all; all 15 resolve to a passage in the same language.
The dropdown remains only as a manual override.

```bash
python scripts/build_sparse_deploy_index.py \
  --input-jsonl data/samples/deploy_msmarco_multilingual.jsonl \
  --no-bootstrap --output qdrant_storage/deploy-lang/chunks.jsonl
python scripts/check_auto_language.py
```

## One-question microphone lifecycle

Partial transcripts are display-only. Auto-send starts only after Scribe emits a
VAD-committed segment (`minSpeechDurationMs=500`, `minSilenceDurationMs=500`);
the connection then closes before retrieval. This prevents background audio
from becoming a second accidental query. The localized **Ask another question**
button starts a fresh single-use token and a clean transcript buffer.

## Secrets

- Put key in `.env` as `ELEVENLABS_API_KEY`
- Never paste keys into chat, commits, or docs
