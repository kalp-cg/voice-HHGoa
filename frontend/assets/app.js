// 1.17.0 is the first version that can request language detection from Scribe.
import { Scribe, RealtimeEvents } from "https://esm.sh/@elevenlabs/client@1.17.0";

// All languages the index can plausibly answer in. Used to narrow Scribe's
// auto-detection from 90+ languages down to this focused set, which
// dramatically reduces confusion between similar-sounding Indic languages
// (e.g. Gujarati heard as Hindi).
const SUPPORTED_LANGUAGES = [
  "en", "hi", "bn", "mr", "ta", "te", "gu", "kn", "ml",
  "pa", "as", "or", "ne", "ur", "sa",
];

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusEl = document.getElementById("status");
const partialEl = document.getElementById("partial");
const transcriptEl = document.getElementById("transcript");
const answerEl = document.getElementById("answer");
const metaEl = document.getElementById("meta");
const sourcesEl = document.getElementById("sources");
const latencyEl = document.getElementById("latency");
const latencyHeroEl = document.getElementById("latency-hero");
const textForm = document.getElementById("text-form");
const textQuery = document.getElementById("text-query");
const modeNote = document.getElementById("mode-note");
const autoSendToggle = document.getElementById("auto-send");
const btnClear = document.getElementById("btn-clear");
const languageSelect = document.getElementById("stt-language");
const btnAgain = document.getElementById("btn-again");
const micLabel = document.getElementById("mic-label");

// Scribe's VAD waits for silence first; this further pause lets the
// COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS event (which carries the detected
// language code) arrive before the question is auto-sent.
// 650ms gives Scribe enough headroom even on slower connections.
const AUTO_SEND_AFTER_COMMIT_MS = 650;
const ASK_AGAIN_LABELS = {
  as: "আকৌ সোধক",
  bn: "আবার জিজ্ঞাসা করুন",
  en: "Ask another question",
  gu: "ફરીથી પૂછો",
  hi: "फिर से पूछें",
  kn: "ಮತ್ತೆ ಕೇಳಿ",
  kok: "परत विचारात",
  ml: "വീണ്ടും ചോദിക്കുക",
  mr: "पुन्हा विचारा",
  ne: "फेरि सोध्नुहोस्",
  or: "ପୁଣି ପଚାରନ୍ତୁ",
  pa: "ਦੁਬਾਰਾ ਪੁੱਛੋ",
  sa: "पुनः पृच्छतु",
  ta: "மீண்டும் கேளுங்கள்",
  te: "మళ్లీ అడగండి",
  ur: "دوبارہ پوچھیں",
};

let connection = null;
let asking = false;
let queuedQuery = null;
let voiceBuffer = "";
let livePartial = "";
let autoSendTimer = null;
const silentClosures = new WeakSet();
// Language the user forced via the dropdown, if any.
let sttLanguage = null;
// Language Scribe reported for the last committed segment.
let detectedLanguage = null;
// Confidence Scribe reported for the detected language.
let detectedConfidence = 0;
let responseLanguage = "en";

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = `status${kind ? ` ${kind}` : ""}`;
}

const MODE = "fast";

// Terms the corpus is built around. Biasing recognition toward them stops
// "Goa" being transcribed as a similar-sounding word.
const KEYTERMS = ["Goa", "Konkan", "India", "MS MARCO"];

// Languages the index can answer in, read from /health. Scribe otherwise
// chooses between 90+ languages and confuses Indic ones that sound close
// (spoken Gujarati transcribed as Devanagari Hindi).
let indexLanguages = [];

async function showRetrievalMode() {
  try {
    const res = await fetch("/health");
    const health = await res.json();
    if (Array.isArray(health.languages)) indexLanguages = health.languages;
    if (!modeNote) return;
    const points = Number(health.index_points || 0).toLocaleString();
    const langs = indexLanguages.join(", ");
    modeNote.textContent =
      health.retrieval_mode === "sparse"
        ? `BM25 + rerank · ${points} chunks${langs ? ` · ${langs}` : ""} · memory-capped host`
        : `Dense + BM25 + RRF + rerank · ${points} chunks`;
  } catch {
    if (modeNote) modeNote.textContent = "Retrieval mode unavailable.";
  }
}

const healthReady = showRetrievalMode();

// Auto-detect judges language from audio alone and reliably confuses Indic
// languages that sound close, so people who speak one of them have to pick it
// by hand. Re-picking before every question is the kind of friction that makes
// a demo look broken, so the choice survives a reload.
const LANGUAGE_PREF_KEY = "voice-rag-goa:stt-language";

function restoreLanguagePreference() {
  let saved = null;
  try {
    saved = localStorage.getItem(LANGUAGE_PREF_KEY);
  } catch {
    return;
  }
  if (saved === null) return;
  const exists = [...languageSelect.options].some((o) => o.value === saved);
  if (exists) languageSelect.value = saved;
}

languageSelect.addEventListener("change", () => {
  try {
    localStorage.setItem(LANGUAGE_PREF_KEY, languageSelect.value);
  } catch {
    // A blocked storage API must not stop the mic from working.
  }
});

restoreLanguagePreference();

function renderSources(sources) {
  if (!sources?.length) {
    sourcesEl.innerHTML = `<p class="empty">No sources.</p>`;
    return;
  }
  sourcesEl.innerHTML = sources
    .map((s, i) => {
      const text = (s.parent_text || s.text || "").slice(0, 280);
      const score = Number(s.rerank_score ?? s.score ?? 0).toFixed(3);
      return `<article class="src"><header>[${i + 1}] ${s.chunk_type || "chunk"} · ${score}</header><p>${escapeHtml(text)}</p></article>`;
    })
    .join("");
}

/**
 * Show the language Scribe detected next to the Live transcript so the user
 * can immediately see if the wrong language was picked and override it.
 */
function showDetectedLanguage() {
  let langInfoEl = document.getElementById("detected-lang-info");
  if (!langInfoEl) {
    langInfoEl = document.createElement("p");
    langInfoEl.id = "detected-lang-info";
    langInfoEl.className = "status";
    langInfoEl.style.cssText = "font-size:0.78rem;margin:0.3rem 0 0;";
    partialEl.parentElement.insertBefore(langInfoEl, partialEl);
  }
  if (detectedLanguage) {
    const confPct = Math.round(detectedConfidence * 100);
    langInfoEl.innerHTML =
      `<span style="color:var(--accent)">🌐 Detected: <strong>${detectedLanguage}</strong> (${confPct}%)</span>`;
  } else {
    langInfoEl.textContent = "🌐 Language: waiting…";
  }
}

function renderLatency(lat) {
  latencyEl.innerHTML = "";
  const rows = Object.entries(lat || {});
  const total = Number(lat?.total_rag);
  if (Number.isFinite(total)) {
    latencyHeroEl.innerHTML = `<span class="latency-value">${total.toFixed(0)}</span><span class="latency-unit">ms RAG</span>`;
    latencyHeroEl.classList.toggle("fast", total < 200);
  } else {
    latencyHeroEl.innerHTML = `<span class="latency-value">—</span><span class="latency-unit">ms RAG</span>`;
    latencyHeroEl.classList.remove("fast");
  }
  if (!rows.length) return;
  for (const [k, v] of rows) {
    const tr = document.createElement("tr");
    if (k === "total_rag") tr.className = "total";
    tr.innerHTML = `<td>${k}</td><td>${Number(v).toFixed(1)}</td>`;
    latencyEl.appendChild(tr);
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function cancelAutoSend() {
  if (autoSendTimer !== null) {
    clearTimeout(autoSendTimer);
    autoSendTimer = null;
  }
}

function closeMic({ silent = false } = {}) {
  const active = connection;
  connection = null;
  if (active) {
    if (silent) silentClosures.add(active);
    active.close();
  }
  btnStart.disabled = false;
  btnStop.disabled = true;
  languageSelect.disabled = false;
}

function resetForNextQuestion() {
  cancelAutoSend();
  voiceBuffer = "";
  livePartial = "";
  detectedLanguage = null;
  detectedConfidence = 0;
  responseLanguage = "en";
  textQuery.value = "";
  partialEl.textContent = "—";
  transcriptEl.textContent = "—";
  answerEl.textContent = "Listening for your next question…";
  metaEl.innerHTML = "";
  sourcesEl.innerHTML = `<p class="empty">No sources yet.</p>`;
  latencyEl.innerHTML = "";
  latencyHeroEl.innerHTML = `<span class="latency-value">—</span><span class="latency-unit">ms RAG</span>`;
  latencyHeroEl.classList.remove("fast");
  btnAgain.hidden = true;
}

function offerAnotherQuestion() {
  micLabel.textContent = "Start mic";
  // Labelled in the language of the answer, so a speaker who does not read
  // English still knows how to continue.
  btnAgain.textContent = ASK_AGAIN_LABELS[responseLanguage] || ASK_AGAIN_LABELS.en;
  btnAgain.hidden = false;
}

function spokenQuestion() {
  return `${voiceBuffer} ${livePartial}`.trim();
}

function stageQuestion(text) {
  textQuery.value = text;
  transcriptEl.textContent = text || "—";
}

function sendStagedQuestion() {
  cancelAutoSend();
  const q = textQuery.value.trim();
  if (!q) return;
  voiceBuffer = "";
  livePartial = "";
  textQuery.value = "";
  // One mic session handles exactly one question. Closing before retrieval
  // prevents room noise from becoming a second accidental query.
  closeMic({ silent: true });
  micLabel.textContent = "Start mic";
  ask(q);
}

/**
 * Send only after Scribe has committed a VAD segment. Partial hypotheses are
 * display-only: room noise must not start a retrieval request.
 */
function scheduleAutoSend() {
  cancelAutoSend();
  if (!autoSendToggle.checked) {
    setStatus("Heard you — press Ask to search", "live");
    return;
  }
  autoSendTimer = setTimeout(() => {
    autoSendTimer = null;
    if (!textQuery.value.trim()) stageQuestion(spokenQuestion());
    sendStagedQuestion();
  }, AUTO_SEND_AFTER_COMMIT_MS);
}

async function ask(query) {
  const q = (query || "").trim();
  if (!q) return;
  if (asking) {
    queuedQuery = q;
    return;
  }
  asking = true;
  transcriptEl.textContent = q;
  setStatus("Retrieving…", "live");
  answerEl.textContent = "Thinking…";
  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: q,
        mode: MODE,
        // Normally nothing is forced: the backend reads the script of the
        // transcript and uses Scribe's guess only where the two agree.
        language: sttLanguage,
        language_hint: detectedLanguage,
      }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Query failed (${res.status})`);
    }
    const data = await res.json();
    answerEl.textContent = data.answer || "—";
    // Prefer the language of the passage that actually answered. Auto-detect
    // recovery can leave several candidates on the query, and showing that
    // list looks like the system could not decide.
    const sourceLang = String(data.sources?.[0]?.language || "").trim();
    const resolvedLang = String(data.query_language || "en").trim() || "en";
    const displayLang =
      sttLanguage || sourceLang || resolvedLang.split(",")[0] || "en";
    responseLanguage = sourceLang || resolvedLang.split(",")[0] || "en";
    const flags = [
      `lang ${displayLang}${sttLanguage ? " (forced)" : " (auto)"}`,
      data.grounded ? "grounded" : "not grounded",
      data.refused ? `refused:${data.refusal_reason || "yes"}` : "answered",
      data.mode,
      `conf ${Number(data.confidence || 0).toFixed(2)}`,
    ].filter(Boolean);
    metaEl.innerHTML = flags
      .map((flag) => `<span class="chip">${escapeHtml(flag)}</span>`)
      .join("");
    renderSources(data.sources);
    renderLatency(data.latency_ms);
    setStatus(data.refused ? "Refused / insufficient context" : "Done", data.refused ? "error" : "live");
  } catch (err) {
    answerEl.textContent = err.message || String(err);
    setStatus(err.message || String(err), "error");
  } finally {
    asking = false;
    if (queuedQuery) {
      const next = queuedQuery;
      queuedQuery = null;
      ask(next);
    } else {
      offerAnotherQuestion();
    }
  }
}

async function fetchScribeToken() {
  const res = await fetch("/api/voice/scribe-token");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Token request failed (${res.status})`);
  }
  const data = await res.json();
  if (!data.token) throw new Error("No token in response");
  return data.token;
}

async function start() {
  resetForNextQuestion();
  micLabel.textContent = "Listening";
  btnStart.disabled = true;
  setStatus("Fetching single-use token…");
  try {
    // The index languages narrow Scribe's detection, so they must be known
    // before the session opens.
    await healthReady;
    const token = await fetchScribeToken();
    const options = {
      token,
      modelId: "scribe_v2_realtime",
      // Commit on detected silence, otherwise the server decides when to
      // finalize and a finished question can sit unsent for seconds.
      commitStrategy: "vad",
      // Long enough to sit through the pause people take mid-question,
      // especially when reading an unfamiliar script aloud. At 0.5s the
      // question was committed half-spoken and retrieval saw a fragment.
      vadSilenceThresholdSecs: 1.6,
      vadThreshold: 0.5,
      minSpeechDurationMs: 500,
      minSilenceDurationMs: 1600,
      includeTimestamps: true,
      noVerbatim: true,
      // Scribe only reports the language it detected when this is on.
      includeLanguageDetection: true,
      keyterms: KEYTERMS,
      microphone: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    };
    // Empty value means auto-detect; the dropdown is only an override for
    // noisy rooms where a short question gets misread.
    const language = languageSelect.value;
    if (language) {
      options.languageCode = language;
    } else {
      // Narrow auto-detection to the languages the index can actually
      // answer in. This is the single most impactful fix for Gujarati
      // being misdetected: searching 15 languages instead of 90+
      // eliminates most confusion between similar-sounding Indic ones.
      options.secondaryLanguages =
        indexLanguages.length > 0 ? indexLanguages : SUPPORTED_LANGUAGES;
    }
    sttLanguage = language || null;
    languageSelect.disabled = true;
    const currentConnection = Scribe.connect(options);
    connection = currentConnection;

    currentConnection.on(RealtimeEvents.SESSION_STARTED, () => {
      setStatus("Listening — speak now", "live");
      btnStop.disabled = false;
    });

    currentConnection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, (data) => {
      if (connection !== currentConnection) return;
      const text = (data.text || "").trim();
      partialEl.textContent = text || "—";
      if (!text) return;
      livePartial = text;
      stageQuestion(spokenQuestion());
      setStatus("Listening…", "live");
    });

    currentConnection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, (data) => {
      if (connection !== currentConnection) return;
      const text = (data.text || "").trim();
      partialEl.textContent = "—";
      livePartial = "";
      if (!text) return;
      // Some ElevenLabs client versions include language info here too.
      // Capture it as a fallback in case WITH_TIMESTAMPS arrives late.
      const earlyLang = (
        data.language_code || data.languageCode || ""
      ).trim().toLowerCase();
      if (earlyLang && !detectedLanguage) {
        detectedLanguage = earlyLang;
        detectedConfidence = Number(
          data.language_probability ?? data.languageProbability ?? 0.5,
        );
        showDetectedLanguage();
      }
      // Segments of one spoken question arrive separately; merge them so the
      // whole sentence is retrieved once instead of per fragment.
      voiceBuffer = `${voiceBuffer} ${text}`.trim();
      stageQuestion(voiceBuffer);
      scheduleAutoSend();
    });

    currentConnection.on(RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS, (data) => {
      if (connection !== currentConnection) return;
      const code = (data.language_code || data.languageCode || "").trim().toLowerCase();
      // With secondaryLanguages narrowed to ~15 languages, even a lower-
      // confidence detection is far more reliable than searching 90+.
      // Threshold lowered from 0.5 → 0.25 to stop dropping valid Gujarati
      // detections that Scribe reports at 0.3–0.4 confidence.
      const confidence = Number(
        data.language_probability ?? data.languageProbability ?? 1,
      );
      if (code && (!Number.isFinite(confidence) || confidence >= 0.25)) {
        detectedLanguage = code;
        detectedConfidence = confidence;
        showDetectedLanguage();
      }
    });

    currentConnection.on(RealtimeEvents.ERROR, (error) => {
      if (connection !== currentConnection) return;
      setStatus(`Error: ${error?.message || error}`, "error");
    });

    currentConnection.on(RealtimeEvents.CLOSE, () => {
      if (connection === currentConnection) {
        connection = null;
        btnStart.disabled = false;
        btnStop.disabled = true;
        languageSelect.disabled = false;
      }
      if (silentClosures.has(currentConnection)) {
        silentClosures.delete(currentConnection);
        return;
      }
      micLabel.textContent = "Start mic";
      setStatus("Mic stopped");
    });
  } catch (err) {
    setStatus(err.message || String(err), "error");
    micLabel.textContent = "Start mic";
    btnStart.disabled = false;
    btnStop.disabled = true;
    languageSelect.disabled = false;
  }
}

function stop() {
  if (!textQuery.value.trim()) stageQuestion(spokenQuestion());
  if (textQuery.value.trim()) {
    // Stopping the mic is an explicit "I'm done talking" signal.
    sendStagedQuestion();
    return;
  }
  closeMic({ silent: true });
  micLabel.textContent = "Start mic";
  setStatus("Stopped");
}

btnStart.addEventListener("click", start);
btnAgain.addEventListener("click", start);
btnStop.addEventListener("click", stop);
textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendStagedQuestion();
});

btnClear.addEventListener("click", () => {
  cancelAutoSend();
  voiceBuffer = "";
  livePartial = "";
  textQuery.value = "";
  partialEl.textContent = "—";
  setStatus("Cleared");
  textQuery.focus();
});

textQuery.addEventListener("input", () => {
  // Typing or editing means the user wants to control the send themselves.
  cancelAutoSend();
  voiceBuffer = textQuery.value.trim();
  livePartial = "";
});
