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

let connection = null;
let asking = false;

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

async function ask(query) {
  const q = (query || "").trim();
  if (!q || asking) return;
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
    connection = Scribe.connect({
      token,
      modelId: "scribe_v2_realtime",
      microphone: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    connection.on(RealtimeEvents.SESSION_STARTED, () => {
      setStatus("Listening — speak now", "live");
      btnStop.disabled = false;
    });

    connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, (data) => {
      partialEl.textContent = data.text || "—";
    });

    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, (data) => {
      const text = (data.text || "").trim();
      partialEl.textContent = "—";
      if (text) ask(text);
    });

    connection.on(RealtimeEvents.ERROR, (error) => {
      setStatus(`Error: ${error?.message || error}`, "error");
    });

    connection.on(RealtimeEvents.CLOSE, () => {
      setStatus("Mic disconnected");
      btnStart.disabled = false;
      btnStop.disabled = true;
      connection = null;
    });
  } catch (err) {
    setStatus(err.message || String(err), "error");
    btnStart.disabled = false;
    btnStop.disabled = true;
  }
}

function stop() {
  if (connection) {
    connection.close();
    connection = null;
  }
  setStatus("Stopped");
  btnStart.disabled = false;
  btnStop.disabled = true;
}

btnStart.addEventListener("click", start);
btnStop.addEventListener("click", stop);
textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  ask(textQuery.value);
});

showRetrievalMode();
