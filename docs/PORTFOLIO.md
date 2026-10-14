# Portfolio narrative

## One-line summary

Built and evaluated an evidence-grounded RAG system over versioned public Irish clinical
guidance, with hybrid retrieval, reranking, exact citation provenance, safe abstention,
and a deployable FastAPI evidence interface.

## CV bullets

- Built an end-to-end Irish clinical RAG research prototype over eight public HSE/NCEC
  documents and 692 checksum-verified passages, preserving document/page/source metadata
  from immutable acquisition through the final UI.
- Implemented and independently evaluated BM25, BGE-small dense retrieval, reciprocal-rank
  fusion, and cross-encoder reranking on 100 synthetic non-patient cases; hybrid retrieval
  improved reviewed Recall@5 from 0.820 for the stronger single retriever to 0.920, while
  reranking reached 0.940 with a measured CPU-latency trade-off.
- Engineered source-grounded generation with exact chunk citations, paragraph-level
  citation verification, deterministic evidence abstention, emergency bypass, and a safe
  extractive fallback for unavailable or unverifiable remote generators.
- Delivered a typed FastAPI service, responsive provenance-first interface, privacy-safe
  structured telemetry, bounded public-component caching, 51 critical tests, reproducible
  experiment artifacts, and a hardened non-root Docker image verified in CI.

## Two-minute interview explanation

The problem was not to make a general medical chatbot. It was to make Irish guidance
auditable. I began with a small authoritative HSE/NCEC source catalog, made downloads
checksum-addressed, and carried provenance through parsing, chunking, retrieval, answers,
and the frontend.

I kept BM25, dense retrieval, reciprocal-rank fusion, and reranking independently runnable
so their contribution could be measured. On 25 authored/source-checked questions, hybrid
retrieval reached 0.920 Recall@5 versus 0.820 for BM25 and 0.780 for dense retrieval.
Reranking reached 0.940, but its median warm CPU latency was about 1.7 seconds versus 68
milliseconds for hybrid, so the main result is a quality/latency trade-off rather than a
claim that the most complex method is always best.

For safety, the service defaults to extractive answers, verifies that every substantive
paragraph cites a retrieved chunk, abstains on weak evidence, and bypasses retrieval for
obvious emergency language. Evaluation artifacts, per-case predictions, corpus checksums,
limitations, failure cases, and the complete reproduction path are in the repository.

## Defensible originality statement

The initial direction was informed by an MIT-licensed medical-RAG repository, but the
Irish source selection, acquisition and manifest model, parsing/chunk schema, English
retrieval stack, fusion, reranking integration, evaluation framework, safety policy,
provider abstraction, caching, API, frontend, tests, experiments, and documentation in
this repository were independently structured and implemented. No upstream code is
currently included. `ATTRIBUTION.md` records the influence and document ownership.

## Claims to avoid

- Do not call the benchmark a clinical validation.
- Do not imply that eight documents cover Irish healthcare guidance comprehensively.
- Do not present deterministic citation/faithfulness checks as medical correctness.
- Do not claim a live public deployment until a URL has passed the documented smoke tests.
- Do not generalise workstation latency to a production service-level objective.
