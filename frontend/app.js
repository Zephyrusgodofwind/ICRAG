const question = document.querySelector("#question");
const ask = document.querySelector("#ask");
const loading = document.querySelector("#loading");
const errorBox = document.querySelector("#error");
const errorMessage = document.querySelector("#error-message");
const retry = document.querySelector("#retry");
const results = document.querySelector("#results");
const preview = document.querySelector("#preview");
const connection = document.querySelector("#connection");
const connectionStatus = document.querySelector("#connection-status");
const isFilePreview = window.location.protocol === "file:";
let requestInFlight = false;

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function formatDate(value, precision) {
  if (!value) return null;
  if (precision === "year") return value.slice(0, 4);
  if (precision === "month") return new Intl.DateTimeFormat("en-IE", {
    month: "short", year: "numeric", timeZone: "UTC"
  }).format(new Date(`${value}T00:00:00Z`));
  return new Intl.DateTimeFormat("en-IE", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC"
  }).format(new Date(`${value}T00:00:00Z`));
}

function showError(message) {
  errorMessage.textContent = message;
  errorBox.classList.remove("hidden");
  retry.classList.toggle("hidden", isFilePreview);
}

function renderEvidence(items, citations) {
  const container = document.querySelector("#evidence");
  if (!items.length) {
    container.innerHTML = '<p class="empty-evidence">No evidence was returned for this response.</p>';
    return;
  }
  const citationByChunk = new Map(citations.map(citation => [citation.chunk_id, citation.citation_id]));
  container.innerHTML = items.map((item, index) => {
    const chunk = item.chunk;
    const citationId = citationByChunk.get(chunk.chunk_id);
    const date = formatDate(
      chunk.last_updated || chunk.publication_date,
      chunk.last_updated ? chunk.last_updated_precision : chunk.publication_date_precision
    );
    const location = [chunk.section, chunk.page_number ? `Page ${chunk.page_number}` : null]
      .filter(Boolean).join(" · ");
    const metadata = [
      date ? `<span>${chunk.last_updated ? "Updated" : "Published"} ${escapeHtml(date)}</span>` : "",
      chunk.document_version ? `<span>Version ${escapeHtml(chunk.document_version)}</span>` : "",
      chunk.topic ? `<span>${escapeHtml(chunk.topic)}</span>` : ""
    ].filter(Boolean).join("");
    return `<details class="evidence-card" ${index === 0 ? "open" : ""}>
      <summary>
        <span class="citation-number ${citationId ? "cited" : "supporting"}">${escapeHtml(citationId || `E${index + 1}`)}</span>
        <span class="source-heading">
          <span class="source-title">${escapeHtml(chunk.source)} — ${escapeHtml(chunk.title)}</span>
          <span class="source-meta">${escapeHtml(location)} · rank ${item.rank} · score ${item.score.toFixed(5)}</span>
          ${citationId ? '<span class="cited-label">Cited in answer</span>' : '<span class="support-label">Supporting retrieval</span>'}
        </span>
      </summary>
      ${metadata ? `<div class="evidence-metadata">${metadata}</div>` : ""}
      <p class="passage">${escapeHtml(chunk.content)}</p>
      <a class="source-link" href="${escapeHtml(chunk.url)}" target="_blank" rel="noopener">Open authoritative source ↗</a>
    </details>`;
  }).join("");
}

function renderMethodDetails(payload, clientLatencyMs) {
  const meta = payload.retrieval_metadata;
  const generation = payload.generation_metadata;
  const parameters = meta.parameters || {};
  const entries = [
    ["Retrieval", meta.method],
    ["Dense encoder", parameters.dense_model],
    ["Reranker", parameters.reranker_model],
    ["Generator", generation.model || generation.provider],
    ["Component cache", parameters.component_cache_hit === undefined
      ? null
      : parameters.component_cache_hit ? "hit" : "miss"],
    ["Reranker status", parameters.reranker_fallback_used
      ? `fallback (${parameters.reranker_fallback_reason || "unavailable"})`
      : null],
    ["Generation fallback", generation.fallback_reason],
    ["Initial candidates", parameters.top_k_initial],
    ["Final evidence", meta.returned],
    ["Retrieval latency", `${meta.latency_ms.toFixed(1)} ms`],
    ["Generation latency", `${generation.latency_ms.toFixed(1)} ms`],
    ["Browser round trip", `${clientLatencyMs.toFixed(1)} ms`],
    ["Corpus fingerprint", parameters.corpus_fingerprint]
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");
  document.querySelector("#method-metadata").innerHTML = entries.map(([label, value]) =>
    `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`
  ).join("");
}

function renderResult(payload, clientLatencyMs) {
  document.querySelector("#answer").textContent = payload.answer;
  document.querySelector("#limitations").textContent = payload.limitations;

  const confidence = document.querySelector("#confidence");
  confidence.textContent = payload.evidence_sufficient
    ? `Evidence confidence ${Math.round(payload.confidence * 100)}%`
    : "Evidence insufficient";
  confidence.classList.toggle("insufficient", !payload.evidence_sufficient);

  const safety = document.querySelector("#safety-status");
  const safetyLabels = {
    grounded: "Citation verified",
    insufficient_evidence: "Abstained safely",
    emergency_escalation: "Emergency guidance"
  };
  safety.textContent = safetyLabels[payload.safety_status] || payload.safety_status;
  safety.dataset.status = payload.safety_status;

  const meta = payload.retrieval_metadata;
  const generation = payload.generation_metadata;
  const fallback = generation.fallback_used ? " · verified fallback" : "";
  document.querySelector("#retrieval-summary").textContent =
    `${meta.method} · ${generation.provider}${fallback} · ${meta.returned} evidence passages`;
  renderMethodDetails(payload, clientLatencyMs);
  renderEvidence(payload.evidence, payload.citations);
}

async function readApiError(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // The status code below remains the safe, useful fallback.
  }
  return `Request failed (${response.status})`;
}

async function runQuery() {
  if (requestInFlight) return;
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

  requestInFlight = true;
  const started = performance.now();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 90000);
  results.classList.add("hidden");
  preview.classList.add("hidden");
  loading.classList.remove("hidden");
  question.setAttribute("aria-busy", "true");
  ask.disabled = true;
  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: value}),
      signal: controller.signal
    });
    if (!response.ok) throw new Error(await readApiError(response));
    const payload = await response.json();
    renderResult(payload, performance.now() - started);
    results.classList.remove("hidden");
    results.focus({preventScroll: true});
    results.scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) {
    preview.classList.remove("hidden");
    const message = error.name === "AbortError"
      ? "The request exceeded 90 seconds and was cancelled."
      : error.message;
    showError(`${message} Check that the API and corpus index are available.`);
  } finally {
    window.clearTimeout(timeout);
    loading.classList.add("hidden");
    question.removeAttribute("aria-busy");
    ask.disabled = false;
    requestInFlight = false;
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
    connection.classList.remove("preview");
    connection.classList.add("connected");
    const semanticStatus = health.semantic_index ? "semantic index ready" : "baseline index";
    connectionStatus.textContent = `API connected · ${health.indexed_chunks} chunks · ${semanticStatus}`;
    document.querySelector("#indexed-count").textContent = health.indexed_chunks;
    document.querySelector("#document-count").textContent = health.indexed_documents;
  } catch {
    connection.classList.remove("connected", "preview");
    connectionStatus.textContent = "API unavailable";
  }
}

ask.addEventListener("click", runQuery);
retry.addEventListener("click", runQuery);
question.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runQuery();
});
document.querySelectorAll(".example").forEach(button => button.addEventListener("click", () => {
  question.value = button.textContent;
  runQuery();
}));

checkConnection();
