# Delivery status

Last updated: 2026-10-07

Legend: `[x]` implemented, `[~]` in progress, `[ ]` not yet implemented.

## Non-negotiable release scope

- [~] Authoritative Irish medical corpus
- [x] Repeatable ingestion with immutable raw storage and manifest
- [x] Metadata-aware section chunking
- [~] Dense retrieval
- [x] BM25 retrieval
- [x] Hybrid retrieval using reciprocal-rank fusion
- [ ] Cross-encoder reranking
- [~] Source-grounded generation with replaceable provider
- [x] Explicit citations with exact chunk provenance verification
- [x] Deterministic emergency escalation and evidence abstention layer
- [ ] 100–150-case evaluation dataset
- [ ] Retrieval and RAG evaluation with measured results
- [x] FastAPI endpoints
- [x] Usable research-style web interface
- [~] Docker Compose configuration implemented; runtime verification pending (Docker unavailable)
- [x] README skeleton and architecture diagram
- [ ] Demo screenshots/video
- [~] Critical component tests (10 passing; 75% measured statement coverage)

## Research questions

Primary: Does hybrid dense + lexical retrieval outperform either retriever alone
on authoritative Irish clinical guidance?

Secondary: How much does cross-encoder reranking improve evidence retrieval
precision over reciprocal-rank fusion alone?

## Deadline guardrail

Optional work (GraphRAG, FHIR, model fine-tuning, agentic web search, and large-scale
PubMed ingestion) remains out of scope until every non-negotiable item is complete.

## Daily delivery discipline

- [x] Git repository initialized and first verified commit prepared
- [ ] GitHub remote configured
- [ ] Today's verified commit pushed and remote acceptance confirmed

Daily GitHub pushes are a non-negotiable delivery requirement. The exact closeout
procedure is defined in `AGENTS.md`.
