// 1.17.0 is the first version that can request language detection from Scribe.
import { Scribe, RealtimeEvents } from "https://esm.sh/@elevenlabs/client@1.17.0";

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusEl = document.getElementById("status");
const partialEl = document.getElementById("partial");
const transcriptEl = document.getElementById("transcript");
const answerEl = document.getElementById("answer");
const metaEl = document.getElementById("meta");
const sourcesEl = document.getElementById("sources");
const latencyEl = document.getElementById("latency");
const textForm = document.getElementById("text-form");
const textQuery = document.getElementById("text-query");
const modeNote = document.getElementById("mode-note");
const autoSendToggle = document.getElementById("auto-send");
const btnClear = document.getElementById("btn-clear");
const languageSelect = document.getElementById("stt-language");
const btnAgain = document.getElementById("btn-again");
const micLabel = document.getElementById("mic-label");

const AUTO_SEND_SILENCE_MS = 900;
const ASK_AGAIN_LABELS = {
  as: "আকৌ সোধক",
  bn: "আবার জিজ্ঞাসা করুন",
  en: "Ask another question",
  gu: "ફરીથી પૂછો",
  hi: "फिर से पूछें",
  kn: "ಮತ್ತೆ ಕೇಳಿ",
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
let responseLanguage = "en";

function setStatus(text, kind = "") {
  statusEl.textContent = text;
  statusEl.className = `status${kind ? ` ${kind}` : ""}`;
}

const MODE = "fast";

async function showRetrievalMode() {
  if (!modeNote) return;
  try {
    const res = await fetch("/health");
    const health = await res.json();
    const points = Number(health.index_points || 0).toLocaleString();
    const langs = Array.isArray(health.languages) ? health.languages.join(", ") : "";
    modeNote.textContent =
      health.retrieval_mode === "sparse"
        ? `BM25 + rerank · ${points} chunks${langs ? ` · ${langs}` : ""} · memory-capped host`
        : `Dense + BM25 + RRF + rerank · ${points} chunks`;
  } catch {
    modeNote.textContent = "Retrieval mode unavailable.";
  }
}

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

function renderLatency(lat) {
  latencyEl.innerHTML = "";
  const rows = Object.entries(lat || {});
  if (!rows.length) return;
  for (const [k, v] of rows) {
    const tr = document.createElement("tr");
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
  responseLanguage = "en";
  textQuery.value = "";
  partialEl.textContent = "—";
  transcriptEl.textContent = "—";
  answerEl.textContent = "Listening for your next question…";
  metaEl.innerHTML = "";
  sourcesEl.innerHTML = `<p class="empty">No sources yet.</p>`;
  latencyEl.innerHTML = "";
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
 * Send once the mic has been quiet for a moment. This runs off partial
 * transcripts as well as committed ones, so a slow or missing commit from the
 * server cannot leave a finished question waiting.
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
  }, AUTO_SEND_SILENCE_MS);
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
    const lang = sttLanguage || detectedLanguage || data.query_language;
    responseLanguage =
      data.sources?.[0]?.language || String(data.query_language || "en").split(",")[0];
    const flags = [
      lang ? `lang ${lang}${sttLanguage ? " (forced)" : " (auto)"}` : null,
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
    const token = await fetchScribeToken();
    const options = {
      token,
      modelId: "scribe_v2_realtime",
      // Commit on detected silence, otherwise the server decides when to
      // finalize and a finished question can sit unsent for seconds.
      commitStrategy: "vad",
      vadSilenceThresholdSecs: 0.5,
      includeTimestamps: true,
      // Scribe only reports the language it detected when this is on.
      includeLanguageDetection: true,
      microphone: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    };
    // Empty value means auto-detect; the dropdown is only an override for
    // noisy rooms where a short question gets misread.
    const language = languageSelect.value;
    if (language) options.languageCode = language;
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
      scheduleAutoSend();
    });

    currentConnection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, (data) => {
      if (connection !== currentConnection) return;
      const text = (data.text || "").trim();
      partialEl.textContent = "—";
      livePartial = "";
      if (!text) return;
      // Segments of one spoken question arrive separately; merge them so the
      // whole sentence is retrieved once instead of per fragment.
      voiceBuffer = `${voiceBuffer} ${text}`.trim();
      stageQuestion(voiceBuffer);
      scheduleAutoSend();
    });

    currentConnection.on(RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS, (data) => {
      if (connection !== currentConnection) return;
      const code = (data.language_code || data.languageCode || "").trim().toLowerCase();
      if (code) detectedLanguage = code;
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

showRetrievalMode();
