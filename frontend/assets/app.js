import { Scribe, RealtimeEvents } from "https://esm.sh/@elevenlabs/client@0.12.2";

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

const AUTO_SEND_SILENCE_MS = 900;

let connection = null;
let asking = false;
let queuedQuery = null;
let voiceBuffer = "";
let livePartial = "";
let autoSendTimer = null;

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
    modeNote.textContent =
      health.retrieval_mode === "sparse"
        ? `Retrieval: BM25 + rerank over ${points} chunks (memory-capped host; dense + RRF run on the full deployment).`
        : `Retrieval: dense + BM25 + RRF + rerank over ${points} chunks.`;
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
      body: JSON.stringify({ query: q, mode: MODE }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Query failed (${res.status})`);
    }
    const data = await res.json();
    answerEl.textContent = data.answer || "—";
    const flags = [
      data.grounded ? "grounded" : "not grounded",
      data.refused ? `refused:${data.refusal_reason || "yes"}` : "answered",
      data.mode,
      `conf ${Number(data.confidence || 0).toFixed(2)}`,
    ];
    metaEl.textContent = flags.join(" · ");
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
      microphone: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    };
    // Auto-detect misreads short questions and can answer in the wrong script,
    // so only omit the language when the user explicitly asks for detection.
    const language = languageSelect.value;
    if (language) options.languageCode = language;
    languageSelect.disabled = true;
    connection = Scribe.connect(options);

    connection.on(RealtimeEvents.SESSION_STARTED, () => {
      setStatus("Listening — speak now", "live");
      btnStop.disabled = false;
    });

    connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, (data) => {
      const text = (data.text || "").trim();
      partialEl.textContent = text || "—";
      if (!text) return;
      livePartial = text;
      stageQuestion(spokenQuestion());
      setStatus("Listening…", "live");
      scheduleAutoSend();
    });

    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, (data) => {
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

    connection.on(RealtimeEvents.ERROR, (error) => {
      setStatus(`Error: ${error?.message || error}`, "error");
    });

    connection.on(RealtimeEvents.CLOSE, () => {
      setStatus("Mic disconnected");
      btnStart.disabled = false;
      btnStop.disabled = true;
      languageSelect.disabled = false;
      connection = null;
    });
  } catch (err) {
    setStatus(err.message || String(err), "error");
    btnStart.disabled = false;
    btnStop.disabled = true;
    languageSelect.disabled = false;
  }
}

function stop() {
  if (connection) {
    connection.close();
    connection = null;
  }
  btnStart.disabled = false;
  btnStop.disabled = true;
  languageSelect.disabled = false;
  if (!textQuery.value.trim()) stageQuestion(spokenQuestion());
  if (textQuery.value.trim()) {
    // Stopping the mic is an explicit "I'm done talking" signal.
    sendStagedQuestion();
    return;
  }
  setStatus("Stopped");
}

btnStart.addEventListener("click", start);
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
