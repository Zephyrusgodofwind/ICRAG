# Delivery status

Last updated: 2026-10-07

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
- [ ] 100–150-case evaluation dataset
- [ ] Retrieval and RAG evaluation with measured results
- [x] FastAPI endpoints
- [x] Usable research-style web interface
- [~] Docker Compose configuration implemented; runtime verification pending (Docker unavailable)
- [x] README skeleton and architecture diagram
- [ ] Demo screenshots/video
- [x] Critical component tests (29 passing; 75.36% statement coverage)

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
- [x] Today's verified commits pushed and remote acceptance confirmed

Daily GitHub pushes are a non-negotiable delivery requirement. The exact closeout
procedure is defined in `AGENTS.md`.
