const question = document.querySelector("#question");
const ask = document.querySelector("#ask");
const loading = document.querySelector("#loading");
const errorBox = document.querySelector("#error");
const results = document.querySelector("#results");
const preview = document.querySelector("#preview");
const connection = document.querySelector("#connection");
const connectionStatus = document.querySelector("#connection-status");
const isFilePreview = window.location.protocol === "file:";

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function renderEvidence(items) {
  const container = document.querySelector("#evidence");
  if (!items.length) {
    container.innerHTML = '<p class="limitations-block">No evidence was returned.</p>';
    return;
  }
  container.innerHTML = items.map((item, index) => {
    const chunk = item.chunk;
    const page = chunk.page_number ? ` · Page ${chunk.page_number}` : "";
    return `<details class="evidence-card" ${index === 0 ? "open" : ""}>
      <summary>
        <span class="citation-number">${index + 1}</span>
        <span><span class="source-title">${escapeHtml(chunk.source)} — ${escapeHtml(chunk.title)}</span>
        <span class="source-meta">${escapeHtml(chunk.section)}${page} · score ${item.score.toFixed(5)}</span></span>
      </summary>
      <p class="passage">${escapeHtml(chunk.content)}</p>
      <a class="source-link" href="${escapeHtml(chunk.url)}" target="_blank" rel="noopener">Open authoritative source ↗</a>
    </details>`;
  }).join("");
}

async function runQuery() {
  const value = question.value.trim();
  errorBox.classList.add("hidden");
  if (value.length < 3) {
    showError("Enter a clinical evidence question of at least three characters.");
    return;
  }
  if (isFilePreview) {
    showError(
      "The visual preview is working. To run evidence searches, start the API and open http://localhost:8000 instead of this local file."
    );
    return;
  }

  results.classList.add("hidden");
  preview.classList.add("hidden");
  loading.classList.remove("hidden");
  ask.disabled = true;
  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: value})
    });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    const payload = await response.json();
    document.querySelector("#answer").textContent = payload.answer;
    document.querySelector("#limitations").textContent = payload.limitations;
    const confidence = document.querySelector("#confidence");
    confidence.textContent = payload.evidence_sufficient
      ? `Evidence confidence ${Math.round(payload.confidence * 100)}%`
      : "Evidence insufficient";
    confidence.classList.toggle("insufficient", !payload.evidence_sufficient);
    const meta = payload.retrieval_metadata;
    const generation = payload.generation_metadata;
    const fallback = generation.fallback_used ? " · safe fallback used" : "";
    document.querySelector("#retrieval-summary").textContent =
      `${meta.method} · ${generation.provider}${fallback} · ${meta.returned} shown · ${meta.latency_ms.toFixed(1)} ms`;
    renderEvidence(payload.evidence);
    results.classList.remove("hidden");
  } catch (error) {
    preview.classList.remove("hidden");
    showError(`${error.message}. Check that the API and corpus index are available.`);
  } finally {
    loading.classList.add("hidden");
    ask.disabled = false;
  }
}

async function checkConnection() {
  if (isFilePreview) {
    connection.classList.add("preview");
    connectionStatus.textContent = "Static visual preview";
    return;
  }
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    const health = await response.json();
    connection.classList.add("connected");
    const semanticStatus = health.semantic_index ? "semantic index ready" : "baseline index";
    connectionStatus.textContent = `API connected · ${health.indexed_chunks} chunks · ${semanticStatus}`;
    document.querySelector("#indexed-count").textContent = health.indexed_chunks;
    document.querySelector("#document-count").textContent = health.indexed_documents;
  } catch {
    connectionStatus.textContent = "API unavailable";
  }
}

ask.addEventListener("click", runQuery);
question.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runQuery();
});
document.querySelectorAll(".example").forEach(button => button.addEventListener("click", () => {
  question.value = button.textContent;
  runQuery();
}));

checkConnection();
