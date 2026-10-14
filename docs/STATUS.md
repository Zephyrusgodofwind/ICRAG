# Delivery status

Last updated: 2026-10-14

Legend: `[x]` implemented, `[~]` in progress, `[ ]` not yet implemented.

## Non-negotiable release scope

- [x] Authoritative Irish medical corpus (current scoped snapshot: 8 HSE/NCEC documents)
- [x] Repeatable ingestion with immutable raw storage and manifest
- [x] Metadata-aware section chunking
- [x] Dense retrieval using a persistent BGE-small index
- [x] BM25 retrieval
- [x] Hybrid retrieval using reciprocal-rank fusion
- [x] Cross-encoder reranking
- [x] Source-grounded generation with replaceable provider
- [x] Explicit citations with exact chunk provenance verification
- [x] Deterministic emergency escalation and evidence abstention layer
- [x] 100–150-case evaluation dataset (100 synthetic, non-patient cases)
- [x] Retrieval and RAG evaluation with measured, reproducible results
- [x] FastAPI endpoints
- [x] Usable research-style web interface
- [~] Hardened Docker/Compose implemented and production image builds successfully in CI;
  Docker Desktop is installed locally, but Windows WSL 2 platform activation/restart is
  still required before local Compose runtime verification
- [x] Release README and system/request-flow architecture diagrams
- [x] Three original demo screenshots from the real API-backed interface
- [x] Critical component and release-contract tests (51 passing; 80% statement coverage)

## Day 1 milestone

Complete: one authoritative HSE document travels through immutable download, parsing,
metadata-aware chunking, indexing, BM25 and dense-baseline retrieval, reciprocal-rank
fusion, API delivery, safety handling, citations, and a usable evidence interface.

Day 1 was committed and pushed to `Zephyrusgodofwind/ICRAG`.

## Day 2 milestone

Implemented and locally verified:

- Expanded the public corpus to six HSE documents and two NCEC guideline volumes.
- Ingested 692 metadata-preserving passages from 21,432,482 bytes of source files.
- Passed the corpus integrity gate with zero errors; six repeated passages were reviewed
  and confirmed as shared NCEC Volume 1/Volume 2 front matter.
- Recorded corpus fingerprint
  `aabbbb57ab1284a786020a9aaae8929f90a9205b7332d5571f9482458185e213`.
- Built a persistent 692 × 384 `BAAI/bge-small-en-v1.5` semantic index.
- Exposed independently selectable BM25, dense, and hybrid retrieval with score/rank
  debugging and provenance.
- Smoke-checked synthetic COPD, UTI, penicillin-allergy, and infection-control questions;
  the expected authoritative document ranked first in the recorded checks. This is a
  functional smoke check, not a formal quality metric or evaluation claim.

## Day 3 milestone

Implemented and locally verified:

- Added `cross-encoder/ms-marco-MiniLM-L6-v2` as a separately selectable reranking
  stage over 20 RRF candidates, preserving pre-rerank ranks and component scores.
- Added answer-level citation validation: every substantive paragraph must cite a known,
  exact retrieved chunk; invalid provider output falls back to the extractive baseline.
- Added a configurable OpenAI-compatible provider for local, hosted, or RunPod models.
  It reads its credential only from `IRISHCLINICALRAG_LLM_API_KEY`; no remote provider
  has been enabled or claimed as tested.
- Normalised private-use PDF bullet glyphs and regenerated the 692-chunk corpus and
  semantic index under fingerprint
  `6a92d8f3b1b30c1fecb3263c1043e08be5248f06daa1eab64d3610c08f08dae1`.
- Measured the reranked path at approximately 14 seconds on cold CPU model loading and
  2.0 seconds warm for the recorded local smoke run. These are engineering timings, not
  retrieval-quality metrics.
- End-to-end API checks returned a cited HSE COPD answer, abstained on an unsupported
  synthetic topic, and bypassed retrieval for an emergency query.

## Day 4 milestone

Complete and locally verified:

- Added a committed 100-case dataset: 25 manually authored, source-checked questions and
  75 deterministic lexical probes, reported as separate cohorts.
- Added independently runnable BM25, dense, hybrid, and hybrid-plus-reranker evaluation
  with Precision@5, Recall@5, Hit Rate@5, MRR, nDCG@5, source-level metrics, and latency.
- Added deterministic grounded-answer checks for evidence sufficiency, citation
  correctness and completeness, extractive faithfulness, expected-source citation, and
  reference token overlap. These are regression checks, not clinical validation.
- Corrected the latency protocol to exclude one-time model loading via one unmeasured
  warm-up query per method.
- Ran 400 retrieval predictions against corpus fingerprint
  `6a92d8f3b1b30c1fecb3263c1043e08be5248f06daa1eab64d3610c08f08dae1`.
- On the 25 reviewed questions, hybrid Recall@5/MRR measured 0.920/0.827 and
  hybrid-plus-reranker measured 0.940/0.837. Median warm CPU latency increased from
  68.3 ms to 1,698.6 ms with reranking.
- Validated the dataset checksum, exact Git and corpus provenance, 400 unique
  predictions, cohort counts, metric bounds, and grounded-answer evaluation completion.
- Documented the exact-passage failures, one conservative RAG abstention, synthetic-probe
  caveats, and lack of clinical validation in `docs/results/day4.md`.

## Day 5 milestone

Complete and locally verified:

- Extended the professional evidence interface with explicit grounded, abstaining, and
  emergency status, source-date/version/topic metadata, citation-used versus supporting
  evidence labels, and expandable retrieval/generation details.
- Added resilient loading, timeout, API-error, retry, and empty-evidence states while
  preserving the no-patient-data and research-only notices.
- Added privacy-safe structured JSON query events that exclude raw questions, answers,
  and passages, plus expanded aggregate request, safety, error, evidence, and latency
  metrics.
- Browser-tested grounded, emergency-bypass, and insufficient-evidence paths on the real
  692-chunk corpus at desktop and 390 x 844 mobile viewports.
- Passed 39 tests with 79% statement coverage and a clean Ruff check. One upstream
  Starlette `TestClient`/httpx deprecation warning remains documented.
- Recorded the full checks and limitations in `docs/DAY5_VERIFICATION.md`.

## Day 6 milestone

Complete and locally verified within available infrastructure:

- Added invalidating, bounded in-process caching for public corpus/configuration/retrieval
  components without retaining raw questions, answers, or query results.
- Added optional pre-readiness model warming; the first ready-state grounded request
  measured 1,936.1 ms and the following request measured 1,636.9 ms end to end on local
  CPU. These are engineering observations, not latency guarantees.
- Added strict readiness, independent liveness, cache observability, safe remote-generation
  fallback, and explicit hybrid fallback when reranking is unavailable.
- Hardened Docker/Compose runtime settings; the production image built successfully in
  GitHub Actions. Docker is not installed locally, so local Compose execution is not
  claimed.
- Re-ran all 100 evaluation cases and 400 predictions. All rankings matched Day 4 exactly;
  reviewed Recall@5/MRR remained 0.820/0.641 (BM25), 0.780/0.660 (dense),
  0.920/0.827 (hybrid), and 0.940/0.837 (hybrid plus reranker).
- Passed 49 tests with 80% statement coverage, clean Ruff, and JavaScript syntax checks.
- Recorded the full protocol, measurements, limitations, and deployment constraint in
  `docs/DAY6_VERIFICATION.md`.

## Day 7 milestone

Complete within the documented deployment boundary:

- Preserved the final 100-case/400-prediction experiment as the canonical result after
  Day 6 reproduced every ranking exactly; no new metric was invented for portfolio polish.
- Rebuilt the README around product value, motivation, real screenshots, public Irish
  sources, methodology, measured results, safety, installation, Docker deployment,
  limitations, roadmap, originality, and reproducibility.
- Added a detailed methodology, a second architecture/request-flow diagram, three original
  screenshots, recruiter/PI portfolio narrative, defensible CV bullets, and an issue-ready
  prioritised roadmap.
- Browser-verified a citation-grounded answer, insufficient-evidence abstention, emergency
  bypass with zero retrieved passages, and the 390 x 844 mobile layout against the real
  692-chunk corpus; zero console errors were observed.
- Added release-contract tests for the required documents/screenshots and the correspondence
  between README headline metrics and the committed machine-readable experiment record.
- Passed 51 tests, Ruff, JavaScript syntax, YAML parsing, corpus-backed API readiness, and
  the real browser acceptance flows.
- Documented the two remaining release boundaries without overstating completion: local
  Compose acceptance awaits Windows WSL 2 platform activation/restart, and no public hosted
  demo target or credentials are configured.

## Research questions

Primary: Does hybrid dense + lexical retrieval outperform either retriever alone
on authoritative Irish clinical guidance?

Secondary: How much does cross-encoder reranking improve evidence retrieval
precision over reciprocal-rank fusion alone?

## Deadline guardrail

Optional work (GraphRAG, FHIR, model fine-tuning, agentic web search, and large-scale
PubMed ingestion) remains out of scope until every non-negotiable item is complete.

## Daily delivery discipline

- [x] Git repository initialized with verified commits
- [x] GitHub remote configured: `Zephyrusgodofwind/ICRAG`
- [x] 2026-10-13 verified Day 4 commits pushed; remote acceptance confirmed
- [x] 2026-10-13 verified Day 5 product-layer commit pushed; remote acceptance confirmed
- [x] 2026-10-13 verified Day 6 commit pushed; Python 3.11, Python 3.13, and production
  Docker image-build gates passed in GitHub Actions
- [x] 2026-10-14 Day 6 closeout verification finalized following successful remote gates;
  delivery is recorded in this repository revision
- [x] 2026-10-14 Day 7 release commit `23fe323` pushed and matched by remote `main`;
  Python 3.11/3.13 quality gates and the production-image build passed in GitHub Actions
  run `38565940902`, with final closeout recorded in this revision

Daily GitHub pushes are a non-negotiable delivery requirement. The exact closeout
procedure is defined in `AGENTS.md`.
