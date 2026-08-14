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

## Secrets

- Put key in `.env` as `ELEVENLABS_API_KEY`
- Never paste keys into chat, commits, or docs
