# Submission kit

## Current links

- GitHub: https://github.com/kalp-cg/voice-HHGoa
- Local demo: http://127.0.0.1:8000
- Public demo (temporary tunnel): run `./scripts/public_demo.sh` and keep that terminal open.
- Recommended permanent host: **Render** (see below)
- Submission form: https://forms.gle/MNvCjcv23Hn2Eeu58

### Deploy on Render (recommended permanent link)

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
   - `DEFAULT_ANSWER_MODE` = `fast`
6. Click **Create Web Service**.
7. Wait for the first build (pip install + first index build, often 5–15 minutes).
8. Open the Render URL (`https://voice-hhgoa.onrender.com` or whatever Render assigns).
9. Check `/health` then ask: “Where is Goa located?”

Notes:
- Free Render apps **sleep when idle**. Wake the site before recording videos or demos.
- First request after sleep can be slow while the service boots and warms embeddings.
- The free disk is ephemeral: redeploys rebuild the small capped sample index automatically.

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

1. Open the HTTPS public URL.
2. Show `/health` reporting the index ready.
3. Ask by voice: “Where is Goa located?”
4. Show transcript, grounded answer, source passages, and stage latency.
5. Ask: “What is the weather in Goa today?” and show refusal.
6. Ask an unsafe query and show the safety refusal.
7. Finish on the latency panel and GitHub URL.

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

- [ ] Public GitHub link opens in an incognito window
- [ ] Public demo URL opens over HTTPS and microphone permission works
- [ ] Video 1 is approximately 90 seconds and shows process
- [ ] Video 2 demonstrates voice → transcript → answer end to end
- [ ] Every team member posted both videos on all three platforms
- [ ] Every post contains `#RAGInGoa`
- [ ] Form fields and links are checked before the one allowed submission
- [ ] Submit before August 22, 2026, 11:59 PM
