const question = document.querySelector("#question");
const ask = document.querySelector("#ask");
const loading = document.querySelector("#loading");
const errorBox = document.querySelector("#error");
const results = document.querySelector("#results");

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  })[character]);
}

function renderEvidence(items) {
  const container = document.querySelector("#evidence");
  if (!items.length) {
    container.innerHTML = '<p class="limitations">No evidence was returned.</p>';
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
  if (value.length < 3) {
    errorBox.textContent = "Enter a clinical evidence question of at least three characters.";
    errorBox.classList.remove("hidden");
    return;
  }
  errorBox.classList.add("hidden");
  results.classList.add("hidden");
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
    document.querySelector("#retrieval-summary").textContent =
      `${meta.method} · ${meta.returned} shown · ${meta.latency_ms.toFixed(1)} ms`;
    renderEvidence(payload.evidence);
    results.classList.remove("hidden");
  } catch (error) {
    errorBox.textContent = `${error.message}. Check that the API and corpus index are available.`;
    errorBox.classList.remove("hidden");
  } finally {
    loading.classList.add("hidden");
    ask.disabled = false;
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
