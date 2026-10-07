# IrishClinicalRAG — 7-Day Project Charter

## 1. Project Identity

**Project name:** IrishClinicalRAG  
**Working subtitle:** Evidence-Grounded Clinical and Biomedical Research Assistant for Irish Healthcare

IrishClinicalRAG is a domain-adapted medical retrieval-augmented generation system focused on Irish clinical guidance and evidence. The goal is not to build another generic “medical chatbot.” The finished project should demonstrate:

- medical-domain data engineering;
- evidence retrieval;
- hybrid information retrieval;
- biomedical NLP;
- retrieval-augmented generation;
- evaluation and benchmarking;
- clinical safety and abstention;
- source provenance;
- API/backend engineering;
- deployment and reproducibility.

The chatbot/interface is only the final interaction layer. The real project is the evidence pipeline, retrieval system, evaluation framework, and safety-aware generation layer.

---

# 2. Primary Goal

Within **7 calendar days**, produce a technically defensible, publicly demonstrable medical AI project suitable for:

1. **Research / PI applications**
   - demonstrates experimental thinking;
   - shows ability to work with biomedical evidence;
   - contains measurable evaluation;
   - contains a reproducible research-style methodology.

2. **MedTech / Pharma / Healthcare AI roles**
   - demonstrates AI engineering;
   - healthcare data ingestion;
   - retrieval systems;
   - LLM integration;
   - deployment;
   - responsible AI.

3. **General AI / ML / Software roles**
   - demonstrates backend engineering;
   - APIs;
   - databases;
   - model integration;
   - testing;
   - Docker;
   - system design.

The project must be strong enough that a recruiter, PI, or engineer can open the repository and understand the engineering and research value without running the code.

---

# 3. Upstream Starting Point

The initial architectural reference/base may be:

`yolo-hyl/medical-rag`

The upstream project is useful for concepts such as:

- hybrid dense + sparse retrieval;
- Milvus integration;
- ingestion pipelines;
- evaluation structure;
- agent/RAG abstractions;
- API patterns.

However, **IrishClinicalRAG must not remain a lightly modified fork**.

The intention is to progressively replace, restructure, rename, simplify, and reimplement enough of the system that the resulting architecture clearly reflects this project’s own objectives.

## Attribution rule

Do not attempt to conceal upstream provenance.

If code from the upstream project remains in the final repository:

- preserve the applicable MIT license and copyright notice where required;
- maintain an `ATTRIBUTION.md` or similar file;
- clearly identify which concepts/components originated upstream;
- clearly identify original additions.

The goal is **independent engineering**, not hidden copying.

If a component is fully reimplemented independently and no upstream code remains in it, it can be treated as an original IrishClinicalRAG component.

---

# 4. Definition of Success

At the end of Day 7, the repository should ideally contain all of the following.

## Non-negotiable

- Irish medical corpus built from authoritative sources.
- Repeatable ingestion pipeline.
- Metadata-aware document chunking.
- Dense retrieval.
- Sparse/BM25 retrieval.
- Hybrid retrieval.
- Reranking.
- Source-grounded answer generation.
- Explicit citations.
- A medical safety / abstention layer.
- Evaluation dataset.
- Retrieval and RAG evaluation.
- Measured experimental results.
- Backend API.
- Usable web interface.
- Dockerised execution.
- Clear README.
- Architecture diagram.
- Demo screenshots or short demo video.
- Tests for critical components.

## Strongly preferred

- live public deployment;
- query routing;
- automated corpus refresh pipeline;
- source-date awareness;
- confidence display;
- latency measurements;
- structured experiment logging;
- comparison of retrieval configurations;
- simple observability dashboard/logs.

## Optional / post-deadline

- GraphRAG;
- full FHIR integration;
- multimodal imaging;
- model fine-tuning;
- LoRA/QLoRA;
- large-scale PubMed ingestion;
- extensive agentic workflows;
- Sonic HPC experiments;
- custom-trained medical retriever.

Do not sacrifice the non-negotiable core to add optional features.

---

# 5. Core Product Principle

The system should answer:

> “What evidence supports this answer?”

not merely:

> “What does the LLM think?”

Every medically meaningful answer should attempt to expose:

- source;
- organisation;
- document title;
- publication/update date where available;
- retrieved passage;
- retrieval score;
- answer confidence or evidence sufficiency;
- limitations.

---

# 6. Initial Irish Evidence Sources

Start small and high quality.

## Priority 1 — HSE

Use authoritative HSE guidance where legally and technically appropriate.

Suggested areas:

- antimicrobial prescribing;
- community antimicrobial guidance;
- hospital antimicrobial guidance;
- respiratory guidance;
- infection control;
- patient safety materials;
- medication-related clinical guidance.

## Priority 2 — NCEC

National Clinical Effectiveness Committee / Irish national clinical guidelines.

Potential topics:

- sepsis;
- COPD;
- clinical handover;
- infection prevention;
- maternity early-warning systems;
- paediatric early-warning systems;
- oncology-related guidance;
- palliative care.

## Priority 3 — HPRA

If time allows:

- Summary of Product Characteristics;
- medicine safety information;
- contraindications;
- warnings;
- adverse effects;
- indications.

## Possible later sources

- NICE;
- EMA;
- PubMed;
- StatPearls;
- WHO;
- peer-reviewed Irish medical literature.

The first release does **not** need millions of documents.

A smaller, high-quality, well-evaluated corpus is preferable.

---

# 7. Corpus Requirements

Every indexed chunk should carry structured metadata.

Minimum metadata schema:

```json
{
  "document_id": "...",
  "chunk_id": "...",
  "source": "HSE",
  "source_type": "clinical_guideline",
  "title": "...",
  "section": "...",
  "url": "...",
  "publication_date": "...",
  "last_updated": "...",
  "retrieved_at": "...",
  "topic": "...",
  "content": "..."
}
```

Recommended additions:

```json
{
  "country": "Ireland",
  "clinical_specialty": "...",
  "document_version": "...",
  "evidence_grade": "...",
  "page_number": "...",
  "language": "en"
}
```

Metadata must survive the entire pipeline:

`source -> parser -> chunk -> embedding -> retrieval -> reranker -> answer -> UI`

---

# 8. Data Ingestion Pipeline

Target architecture:

```text
Source discovery
      ↓
Document downloader / scraper
      ↓
Raw immutable storage
      ↓
Parser
      ↓
Cleaning
      ↓
Document normalisation
      ↓
Section-aware chunking
      ↓
Metadata enrichment
      ↓
Validation
      ↓
Embedding + sparse indexing
      ↓
Vector / retrieval database
```

Suggested directory structure:

```text
data/
├── raw/
├── processed/
├── chunks/
├── eval/
└── manifests/
```

Raw documents should never be silently overwritten.

Maintain a manifest containing:

- source URL;
- checksum;
- acquisition date;
- processing status;
- document version;
- number of chunks.

---

# 9. Chunking

Avoid naïve fixed-character splitting when possible.

Preferred order:

1. preserve document title;
2. preserve heading hierarchy;
3. preserve paragraph boundaries;
4. preserve tables where meaningful;
5. chunk only after semantic structure is identified.

Initial target:

- roughly 300–700 tokens per chunk;
- modest overlap;
- experiment rather than assume the optimal value.

Chunk size is an experimental variable.

---

# 10. Retrieval Architecture

The minimum retrieval stack should be:

```text
User query
    ↓
Query preprocessing
    ↓
┌────────────────────┐
│ Dense retrieval    │
└────────────────────┘
          +
┌────────────────────┐
│ Sparse / BM25      │
└────────────────────┘
          ↓
Fusion
          ↓
Candidate set
          ↓
Cross-encoder reranker
          ↓
Top-k evidence
```

## Dense retrieval

Possible models:

- BGE-M3;
- biomedical SentenceTransformer;
- MedCPT;
- another justified embedding model.

Do not lock this choice prematurely.

## Sparse retrieval

BM25 must be retained as a baseline.

## Fusion

Possible approaches:

- Reciprocal Rank Fusion;
- weighted score fusion;
- learned weighting later.

Start with RRF unless there is a strong reason not to.

## Reranking

Use a cross-encoder where practical.

Reranking is one of the project’s important differentiators and should not be removed unless time/compute makes it impossible.

---

# 11. RAG Generation Layer

The generation model should not be the research contribution.

The system must work with a replaceable LLM interface.

Potential providers:

- OpenAI;
- Azure OpenAI;
- Gemini;
- Groq;
- local Ollama;
- vLLM / RunPod-hosted model;
- later Sonic HPC.

Implement an abstraction such as:

```python
class LLMProvider:
    def generate(self, messages, context, **kwargs):
        ...
```

Avoid deeply coupling retrieval logic to a particular provider.

---

# 12. Answer Contract

The final answer should follow a predictable structure.

Example:

```json
{
  "answer": "...",
  "evidence": [...],
  "citations": [...],
  "confidence": 0.86,
  "evidence_sufficient": true,
  "limitations": "...",
  "retrieval_metadata": {...}
}
```

The UI can render this cleanly.

---

# 13. Clinical Safety Layer

This is mandatory.

The project is an evidence assistant, not an autonomous diagnostic system.

It should include:

## Evidence insufficiency

If evidence is weak:

> “I could not find sufficiently strong evidence in the indexed Irish clinical sources to answer this reliably.”

## Emergency escalation

For obvious emergency symptoms, the system should avoid pretending RAG retrieval replaces emergency care.

## Unsupported claims

The model should be instructed to avoid claims unsupported by retrieved evidence.

## Citation verification

The system should check that key medical claims correspond to retrieved evidence.

## Scope disclaimer

Display a concise statement that the tool is:

- for research/educational decision support;
- not a replacement for clinical judgement;
- not a certified medical device.

Do not make exaggerated claims such as:

- “diagnoses disease accurately”;
- “prevents hallucinations”;
- “clinically validated”;

unless those claims are truly supported.

---

# 14. Evaluation — Mandatory

A serious evaluation layer is one of the most important parts of IrishClinicalRAG.

## Evaluation dataset

Target:

**100–150 questions** for the 7-day release.

Questions should be grounded in indexed documents.

Possible categories:

```text
Antimicrobial prescribing
Sepsis
Respiratory disease / COPD
Medication safety
Infection control
Paediatrics
Clinical handover
Oncology
Palliative care
```

Each evaluation case should ideally contain:

```json
{
  "question": "...",
  "reference_answer": "...",
  "expected_sources": [...],
  "category": "...",
  "difficulty": "...",
  "notes": "..."
}
```

---

# 15. Retrieval Evaluation

Evaluate retrieval separately from generation.

Possible metrics:

- Recall@k;
- Precision@k;
- MRR;
- nDCG;
- Hit Rate;
- source recall.

Test several retrieval pipelines.

Minimum experiment matrix:

```text
A. BM25
B. Dense
C. Hybrid
D. Hybrid + reranker
```

Recommended:

```text
E. Hybrid + query expansion + reranker
```

Do not declare one method superior without measured evidence.

---

# 16. RAG Evaluation

Suggested metrics:

- Faithfulness;
- Answer Relevancy;
- Context Precision;
- Context Recall;
- Citation correctness;
- Citation completeness.

RAGAS may be used, but do not treat an LLM judge as absolute ground truth.

Include a small manual evaluation subset.

Example:

```text
25 manually reviewed questions
```

Rate:

- medical correctness;
- evidence support;
- citation quality;
- completeness;
- unsafe claims.

---

# 17. Experimental Discipline

Every experiment should be reproducible.

Create:

```text
experiments/
```

Store:

```text
config
model
embedding model
retriever
reranker
chunk size
top-k
prompt version
metrics
timestamp
git commit
```

Prefer YAML/JSON configs.

Example:

```yaml
experiment: hybrid_rerank_v1

retrieval:
  dense_model: BAAI/bge-m3
  sparse: bm25
  fusion: rrf
  top_k_initial: 20
  reranker: cross-encoder
  top_k_final: 5

chunking:
  target_tokens: 500
  overlap: 80
```

---

# 18. API

Recommended backend:

**FastAPI**

Minimum endpoints:

```text
GET  /health
POST /query
POST /retrieve
GET  /sources
GET  /metrics
```

Optional:

```text
POST /feedback
POST /admin/reindex
GET  /experiments
```

Keep retrieval callable independently of generation.

This matters for testing and research.

---

# 19. Frontend

The interface should look like a research/clinical evidence tool rather than a generic ChatGPT clone.

Recommended layout:

```text
-----------------------------------------
IrishClinicalRAG
Evidence-grounded Irish clinical AI
-----------------------------------------

Question

[ Ask ]

-----------------------------------------
Answer
-----------------------------------------

Evidence
[1] HSE ...
Relevant passage...

[2] NCEC ...
Relevant passage...

-----------------------------------------
Retrieval details
Retriever: Hybrid
Candidates: 20
Reranked: 5
Latency: ...
-----------------------------------------
```

Useful UI elements:

- evidence cards;
- expandable source passages;
- confidence / evidence sufficiency;
- source organisation;
- source date;
- clickable URL;
- retrieval method;
- latency;
- model details.

Avoid excessive decorative animations.

Professional > flashy.

---

# 20. Observability

At minimum log:

- query;
- retrieval latency;
- generation latency;
- total latency;
- retrieved documents;
- scores;
- model;
- token count;
- error status.

Do not log private medical data in a production-like environment.

For public demos, add a short privacy notice.

---

# 21. Testing

Minimum test categories:

```text
tests/
├── test_ingestion.py
├── test_chunking.py
├── test_retrieval.py
├── test_reranking.py
├── test_citations.py
├── test_api.py
└── test_safety.py
```

Important invariants:

- every returned evidence item has valid metadata;
- citation IDs map to retrieved documents;
- empty retrieval does not produce confident medical advice;
- API schema is stable;
- duplicate documents are detected;
- ingestion is deterministic where possible.

---

# 22. Deployment

Target:

```text
Docker
```

The complete system should ideally start with something similar to:

```bash
docker compose up
```

Possible services:

```text
app
milvus
supporting Milvus services
frontend
```

If Milvus proves unnecessarily heavy for public deployment, the production demo may use another vector backend as long as the research version preserves equivalent retrieval functionality.

Deployment architecture may change if needed.

---

# 23. Compute Strategy

## Immediate

Use local CPU/GPU where possible.

Use RunPod when:

- reranking;
- embedding large document batches;
- local LLM inference;
- evaluation;

would otherwise be too slow.

## Near future

Once Sonic HPC access is available, it can be used for:

- larger embedding experiments;
- MedCPT experiments;
- larger local LLMs;
- retriever fine-tuning;
- large evaluation runs;
- PubMed-scale work.

The initial 7-day release must **not depend on Sonic access**.

---

# 24. Repository Structure

This is a starting suggestion, not a rigid requirement.

```text
IrishClinicalRAG/
│
├── README.md
├── LICENSE
├── ATTRIBUTION.md
├── pyproject.toml
├── docker-compose.yml
│
├── configs/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── chunks/
│   ├── eval/
│   └── manifests/
│
├── src/
│   └── irishclinicalrag/
│       ├── ingestion/
│       ├── parsing/
│       ├── chunking/
│       ├── embeddings/
│       ├── retrieval/
│       ├── reranking/
│       ├── generation/
│       ├── citations/
│       ├── safety/
│       ├── evaluation/
│       ├── api/
│       └── observability/
│
├── frontend/
│
├── scripts/
│
├── experiments/
│
├── tests/
│
├── docs/
│   ├── architecture/
│   ├── methodology/
│   └── results/
│
└── notebooks/
```

Notebooks should be used for exploration, not as the primary production architecture.

---

# 25. Originality Requirements

The finished project should have its own identity.

Strongly recommended:

- new package/module names;
- new directory structure;
- new configuration system;
- new ingestion layer;
- Irish-specific metadata model;
- independent retrieval abstraction;
- independent evaluation framework;
- independent API schema;
- new frontend;
- new prompts;
- new documentation;
- new architecture diagrams;
- new tests.

Do not copy:

- upstream README wording;
- screenshots;
- logos;
- UI;
- documentation;
- example results;
- branding.

If code is reused, keep proper attribution.

---

# 26. What “Make It My Own” Means

Good:

> “I used an MIT-licensed medical RAG implementation as an architectural reference, then replaced the dataset, ingestion, English retrieval stack, metadata schema, evaluation framework, safety layer, API and frontend, and benchmarked the resulting Irish clinical system.”

Bad:

> “I wrote the whole project from scratch.”

if substantial upstream code remains.

The strongest position is transparent and technically defensible.

---

# 27. README Requirements

The README should eventually include:

1. project summary;
2. demo;
3. motivation;
4. architecture;
5. Irish data sources;
6. ingestion pipeline;
7. retrieval methodology;
8. generation methodology;
9. evaluation dataset;
10. experiments;
11. results;
12. safety;
13. installation;
14. deployment;
15. limitations;
16. roadmap;
17. upstream attribution.

The first screen of the README should communicate value immediately.

Example:

```text
IrishClinicalRAG

Evidence-grounded clinical and biomedical research assistant
for Irish healthcare guidance.

Hybrid retrieval • Biomedical NLP • Reranking
Citation verification • RAG evaluation • FastAPI • Docker
```

---

# 28. Results Before Claims

Do not invent metrics.

Do not insert placeholder metrics into the final README unless they are visibly labelled placeholders.

Once experiments run, report real numbers such as:

```text
Retriever          Recall@5   MRR   Faithfulness
BM25
Dense
Hybrid
Hybrid + reranker
```

Include:

- evaluation sample size;
- corpus version;
- model;
- date;
- methodology.

---

# 29. 7-Day Execution Strategy

This schedule is intentionally flexible.

The important rule is:

> each day should end with a working system that is better than the previous day.

---

## Day 1 — Foundation

Primary objective:

**Own the architecture.**

Target outcomes:

- create IrishClinicalRAG repository;
- inspect upstream architecture;
- identify reusable ideas vs code;
- establish independent package structure;
- establish configs;
- establish environment;
- make baseline app run;
- implement source downloader/parser skeleton;
- ingest first Irish documents.

Do not spend the entire day refactoring.

By the end of Day 1, at least one Irish document should travel through:

```text
download -> parse -> chunk -> index -> retrieve
```

---

## Day 2 — Corpus and Retrieval

Target:

- ingest meaningful HSE/NCEC corpus;
- validate metadata;
- dense embeddings;
- BM25;
- hybrid retrieval;
- retrieval CLI/debug view.

By end of day:

A query should return relevant Irish evidence with source metadata.

---

## Day 3 — Reranking + RAG

Target:

- fusion;
- reranking;
- LLM generation;
- citations;
- evidence sufficiency;
- basic safety.

By end of day:

The system should answer questions with cited Irish evidence.

This is the first true MVP.

---

## Day 4 — Evaluation

Target:

- create evaluation dataset;
- retrieval metrics;
- RAG metrics;
- experiment runner;
- first comparison table.

This day is non-negotiable.

Do not postpone evaluation to the end.

---

## Day 5 — Product Layer

Target:

- FastAPI;
- frontend;
- evidence cards;
- confidence display;
- source links;
- error handling;
- logs.

Focus on clarity.

---

## Day 6 — Deployment + Reliability

Target:

- Docker;
- public deployment if feasible;
- tests;
- latency improvements;
- caching;
- failure handling;
- larger evaluation run.

Freeze major architecture changes after this point unless something is broken.

---

## Day 7 — Research + Portfolio Polish

Target:

- final experiments;
- final metrics;
- README;
- diagrams;
- methodology page;
- screenshots;
- demo video;
- CV bullets;
- repository cleanup;
- issues/roadmap.

No risky new features.

---

# 30. Deadline Protection Rules

Because the deadline is strict:

## If behind schedule

Remove in this order:

1. agentic Web search;
2. fancy UI;
3. HPRA;
4. query expansion;
5. advanced observability;
6. automated corpus refresh;
7. public deployment.

Never remove:

1. authoritative Irish corpus;
2. ingestion;
3. hybrid retrieval;
4. reranking if technically possible;
5. citations;
6. safety;
7. evaluation;
8. reproducibility;
9. documentation.

---

# 31. Technical Decisions That May Change

These are not sacred.

The following may be replaced if justified:

- Milvus;
- embedding model;
- LLM;
- reranker;
- frontend framework;
- parser;
- chunk size;
- prompt design;
- deployment provider;
- evaluation tooling.

Do not waste time preserving a technology simply because the initial upstream repo used it.

---

# 32. Technical Decisions That Should Not Change

The project should remain:

- Irish clinical evidence focused;
- evidence-grounded;
- retrieval-centric;
- evaluated;
- source-transparent;
- reproducible;
- safety-aware;
- deployable;
- professionally documented.

These are the project identity.

---

# 33. Potential Research Questions

The project should eventually answer at least one real research question.

Possible examples:

### RQ1

Does hybrid dense + lexical retrieval outperform dense retrieval alone for Irish national clinical guidance?

### RQ2

Do biomedical embedding models outperform general embedding models on Irish clinical guidance retrieval?

### RQ3

How much does cross-encoder reranking improve evidence retrieval precision?

### RQ4

Does retrieval from national clinical guidance improve answer grounding compared with general biomedical corpora?

### RQ5

What is the effect of chunking strategy on citation correctness and retrieval recall?

The 7-day release only needs one or two properly investigated questions.

---

# 34. Possible Future Extension After Deadline

Once the initial project is live:

## Research track

- MedRAG/MIRAGE compatibility;
- PubMed + Irish guidance comparisons;
- retriever fine-tuning;
- custom benchmark paper;
- multi-corpus routing.

## MedTech track

- FHIR;
- EHR integration;
- structured clinical decision support;
- audit logs;
- role-based access control.

## ML track

- biomedical retriever training;
- uncertainty calibration;
- learned reranking;
- retrieval distillation.

## Infrastructure track

- Sonic HPC;
- vLLM;
- large-scale corpus indexing;
- distributed evaluation.

---

# 35. Commit / Development Discipline

Use meaningful commits.

Examples:

```text
feat: add HSE guideline ingestion
feat: implement BM25 retriever
feat: add RRF hybrid fusion
feat: integrate cross-encoder reranker
eval: add retrieval benchmark
test: verify citation provenance
docs: add architecture diagram
```

Avoid:

```text
update
changes
fix stuff
final
final2
```

Use branches when useful, but do not create process overhead.

---

# 36. Coding Standard

Prefer:

- typed Python;
- Pydantic models;
- clear interfaces;
- dependency injection/configuration;
- small testable modules;
- structured logging;
- environment variables for secrets.

Avoid:

- API keys in source;
- giant notebook pipelines;
- hard-coded paths;
- hard-coded model names throughout the code;
- medical logic buried inside UI code.

---

# 37. Security / Privacy

The public project should use public documents and synthetic/demo questions.

Do not store:

- real patient data;
- personal health records;
- identifiable clinical records.

If future work introduces health records, privacy architecture must be redesigned accordingly.

---

# 38. Final Portfolio Standard

Before calling the project complete, ask:

### Can a PI see research ability?

There should be:

- hypothesis;
- benchmark;
- experimental comparison;
- metrics;
- interpretation.

### Can an ML engineer see engineering ability?

There should be:

- modular code;
- retrieval stack;
- APIs;
- tests;
- Docker;
- configuration.

### Can a MedTech recruiter see healthcare relevance?

There should be:

- Irish clinical evidence;
- provenance;
- safety;
- clinical limitations;
- evidence grounding.

### Can a general recruiter understand it in 30 seconds?

The README must make this obvious.

---

# 39. Final Definition of “Done”

The project is done for the 7-day release when:

- a recruiter can open a live demo;
- ask a supported Irish clinical question;
- receive an evidence-grounded answer;
- inspect the exact sources;
- see the retrieval method;
- see that the system can abstain;
- inspect measurable evaluation results;
- open the GitHub repository;
- understand the architecture;
- reproduce the system;
- understand what was original work;
- understand what upstream project influenced the initial architecture.

The project does not need to be perfect.

It needs to be:

**credible, measurable, reproducible, deployed, and clearly yours.**

---

# 40. Working Rule for the Next 7 Days

When choosing between two tasks, prefer the one that increases one of:

1. evidence quality;
2. retrieval quality;
3. evaluation quality;
4. reproducibility;
5. recruiter/PI comprehensibility.

Everything else is secondary.

---

## Current starting decision

**Build IrishClinicalRAG using the yolo-hyl medical-rag project as an initial architectural reference/base, while progressively replacing the implementation with an Irish-specific, independently structured system.**

Immediate first milestone:

```text
One authoritative Irish clinical document
→ parsed
→ chunked
→ metadata preserved
→ embedded/indexed
→ retrieved correctly
```

Once that works, scale outward.

