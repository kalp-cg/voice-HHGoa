# Submission kit

## Current links

- GitHub: https://github.com/kalp-cg/voice-HHGoa
- **Public demo (permanent): https://voice-hhgoa.onrender.com** ← use this on the form
- Local demo: http://127.0.0.1:8000
- Public demo (temporary fallback tunnel): run `./scripts/public_demo.sh` and keep that terminal open.
- Submission form: https://forms.gle/MNvCjcv23Hn2Eeu58

Verified live on 2026-08-15:

| Check | Result |
|---|---|
| `/health` | `status: ok`, `index_points: 3432`, `retrieval_mode: sparse` |
| Balanced sparse evaluation | 1,965/1,965 paired queries grounded; 1,965/1,965 same-language top hit |
| English query | grounded answer |
| Hindi query (`गोवा कहाँ है?`) | grounded Hindi answer |
| Mixed-script Gujarati (`Goa ક્યાં છે?`) | grounded Gujarati answer |
| Unsafe query | refused |
| `/api/voice/scribe-token` | 200 with a single-use token (ElevenLabs key active) |

### Render Free memory mode

Render Free caps RAM at 512 MB, which the FastEmbed ONNX model alone exceeds.
The deployed image therefore runs `RETRIEVAL_MODE=sparse`: BM25 + rerank +
guardrails over a balanced 1,965-record / 3,432-chunk index baked at Docker build
time (~52 MB BM25 RSS in the local sparse API check). It contains official small IndicMSMARCO benchmark rows
plus the curated Goa fact in every supported language.
`/api/retrieve/dense` and `/api/retrieve/hybrid` return 501 on Free. Full hybrid
retrieval runs locally and on any host with ≥2 GB RAM.

When demoing, say retrieval is hybrid in the full system and BM25-only on the
free host; do not present the free host's numbers as the hybrid benchmark.

### Deploy on Render (how it was set up)

1. Open https://dashboard.render.com and sign up / log in (GitHub login is easiest).
2. Click **New +** → **Web Service**.
3. Connect the repo `kalp-cg/voice-HHGoa` (authorize GitHub if asked).
4. Settings:
   - **Name:** `voice-hhgoa`
   - **Language / Runtime:** Docker
   - **Branch:** `main`
   - **Region:** Singapore (or closest to you)
   - **Instance type:** Free
5. **Environment** → Add:
   - `ELEVENLABS_API_KEY` = your ElevenLabs key (from local `.env`)
   - `QDRANT_PATH` = `qdrant_storage/deploy`
   - `RETRIEVAL_MODE` = `sparse`
   - `SKIP_STARTUP_WARMUP` = `1`
   - `DEFAULT_ANSWER_MODE` = `fast`
6. Click **Create Web Service**.
7. Wait for the first build (pip install + build-time index, roughly 3–8 minutes).
8. Open the Render URL (`https://voice-hhgoa.onrender.com` or whatever Render assigns).
9. Check `/health` then ask: “Where is Goa located?”

Notes:
- Free Render apps **sleep when idle**. Wake the site before recording videos or demos.
- First request after sleep can be slow while the container boots.
- The free disk is ephemeral: the index lives in the image, so redeploys always have it.
- Dropping `RETRIEVAL_MODE=sparse` on a 512 MB instance brings back the OOM.

## Video 1 — team/process (90 seconds)

1. **0–10 s:** State the problem: voice question → MSMARCO-XI retrieval → grounded answer.
2. **10–25 s:** Show the GitHub history and milestone-based workflow.
3. **25–45 s:** Show capped streaming ingestion and the four chunk strategies.
4. **45–65 s:** Show dense + BM25 + RRF + reranking and guardrails.
5. **65–80 s:** Show the 190-query benchmark: P50/P70/P100.
6. **80–90 s:** State what each team member built and show the final repo URL.

Do not claim that all 55.6 GB was indexed. Say that the corpus is streamed and
capped to fit the target hardware, with measured scale-up checkpoints.

## Video 2 — product demo

1. Open https://voice-hhgoa.onrender.com (load it once beforehand so it is awake).
2. Show `/health` reporting the index ready.
3. Ask by voice: “Where is Goa located?” Leave **Language** on *Auto-detect*.
4. Ask the same question in Hindi / Gujarati / Tamil. If Scribe writes the wrong
   script, the backend still recovers from the words themselves. The badge under
   the answer shows `lang xx (auto)`. The live source sample is 1,965 records /
   3,432 chunks, not the 55.6 GB dump.
5. Show transcript, grounded answer, source passages, and stage latency.
6. Ask: “What is the weather in Goa today?” and show refusal.
7. Ask an unsafe query and show the safety refusal.
8. Finish on the latency panel and GitHub URL.

## Required posting caption

> We built Voice RAG Goa: ElevenLabs realtime speech-to-text, multi-strategy
> MSMARCO-XI chunking, dense + BM25 hybrid retrieval, RRF, reranking,
> grounding guardrails, and measured P50/P70/P100 latency.
>
> GitHub: https://github.com/kalp-cg/voice-HHGoa
>
> #RAGInGoa

Every individual team member must post both videos to:

- Instagram (at least one account public)
- X
- LinkedIn

Every post must include `#RAGInGoa`.

## Final form checklist

- [x] Public GitHub link opens in an incognito window
- [x] Public demo URL opens over HTTPS (https://voice-hhgoa.onrender.com) and the STT token endpoint returns 200
- [x] Live corpus contains 3,432 balanced multilingual chunks and passes the paired-query evaluation
- [ ] Video 1 is approximately 90 seconds and shows process
- [ ] Video 2 demonstrates voice → transcript → answer end to end
- [ ] Every team member posted both videos on all three platforms
- [ ] Every post contains `#RAGInGoa`
- [ ] Form fields and links are checked before the one allowed submission
- [ ] Submit before August 22, 2026, 11:59 PM
