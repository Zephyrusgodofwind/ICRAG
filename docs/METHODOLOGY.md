# Methodology

This page describes the reproducible research method used for the seven-day
IrishClinicalRAG release. It separates measured engineering evidence from medical claims.

## Scope and research questions

The system is restricted to public Irish healthcare guidance and synthetic, non-patient
questions.

Primary question: does reciprocal-rank fusion of sparse and dense retrieval outperform
either retriever alone on the reviewed Irish-guidance benchmark?

Secondary question: how much does a general-purpose cross-encoder improve exact-passage
retrieval, and what CPU-latency cost does it introduce?

## Corpus acquisition and versioning

`configs/sources.json` is the human-reviewed source catalog. Each entry identifies a
public HSE or NCEC resource and its topic, organisation, title, dates when available, URL,
and expected content type.

Acquisition is intentionally immutable:

1. Download bytes from the configured authoritative URL.
2. Calculate SHA-256 before assigning the storage path.
3. Store the blob under its checksum without silently replacing an existing blob.
4. Append acquisition metadata to the local manifest.
5. Bind the validated corpus to checksums and a combined fingerprint in
   `data/manifests/corpus-lock.json`.

Raw downloads and generated corpus artifacts are ignored by Git because they are large
and reproducible. The lock file, source catalog, and validation report are committed.

## Parsing, chunking, and integrity

PDF and HTML adapters normalise text while preserving source identifiers, organisation,
title, URL, publication/update fields, page, and section. Section-aware chunks target 500
tokens with 80-token overlap and an 80-token minimum. Stable chunk identifiers are derived
from their provenance and content.

The integrity gate rejects missing required metadata, invalid source relationships,
checksum disagreement, duplicate identifiers, empty content, and index/corpus fingerprint
mismatch. Repeated text is reported for review rather than silently discarded; six
repetitions in the current snapshot were confirmed as shared front matter across two NCEC
volumes.

## Retrieval configurations

Every configuration is independently selectable and evaluable:

1. **BM25:** lexical term matching over validated chunks.
2. **Dense:** cosine similarity over a persistent 384-dimensional
   `BAAI/bge-small-en-v1.5` index.
3. **Hybrid:** reciprocal-rank fusion of BM25 and dense ranks with `rrf_k=60`, avoiding
   invalid direct comparison of unrelated score scales.
4. **Hybrid + reranker:** rerank 20 fused candidates using
   `cross-encoder/ms-marco-MiniLM-L6-v2`, then return five.

The API returns final rank/score plus component ranks and scores so retrieval decisions
remain inspectable. If the optional reranker cannot load, the system declares an explicit
fallback to the hybrid result.

## Evidence sufficiency, generation, and citations

The default generation provider is deterministic and extractive. It selects relevant
sentences from retrieved passages and attaches the corresponding citation IDs. Generation
providers implement a replaceable contract; an OpenAI-compatible provider may target a
hosted endpoint, local server, or RunPod without changing retrieval.

Before an answer is released, the service checks that:

- evidence meets the configured sufficiency threshold;
- each citation maps to an exact retrieved chunk;
- every substantive answer paragraph has at least one known citation;
- the extractive fallback uses only text from retrieved evidence.

Unverifiable provider output is replaced with the grounded extractive answer. Missing or
weak evidence produces an abstention. Obvious emergency language bypasses retrieval and
directs the user to 112/999 or emergency care in Ireland.

## Evaluation design

The committed dataset contains 100 synthetic, non-patient cases:

- 25 manually authored, source-checked questions with expected source and passage labels;
- 75 deterministic lexical probes generated from rare terms in labelled passages.

The cohorts are always reported separately because the lexical probes are easier and are
primarily a test of indexing and provenance plumbing. Each retrieval method is warmed once
without measurement, then evaluated on every case at `top_k=5`.

Reported retrieval measures are Precision@5, Recall@5, Hit Rate@5, MRR, nDCG@5,
source-level equivalents, and mean/median/p95 warm latency. Grounded answers are checked
for evidence sufficiency, exact citation correctness, citation completeness, extractive
faithfulness, expected-source citation, and reference token overlap. No clinician rating
or LLM-as-judge score is represented.

The canonical run records:

- dataset SHA-256 and cohort counts;
- exact Git commit and corpus fingerprint;
- model and prompt identifiers;
- retrieval and chunk parameters;
- aggregate metrics and all 400 per-case predictions.

## Interpretation

On the 25 reviewed questions, hybrid retrieval reached Recall@5 0.920 and MRR 0.827,
compared with 0.820/0.641 for BM25 and 0.780/0.660 for dense retrieval. Reranking reached
0.940/0.837 but increased median warm CPU latency from 68.3 ms to 1,698.6 ms.

This supports the limited conclusion that fusion improved reviewed exact-passage retrieval
on this snapshot and that reranking added a small quality gain at a large CPU cost. It
does not establish clinical accuracy, generalisability, or deployment safety.

## Reproduction and audit trail

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,ml]"
irishclinicalrag ingest configs/sources.json
irishclinicalrag validate configs/sources.json
irishclinicalrag build-index
irishclinicalrag build-eval
irishclinicalrag evaluate
pytest
```

Compare the resulting corpus fingerprint and evaluation checksum with the committed lock
and metrics. `docs/results/day4.md` contains the full failure audit, while
`experiments/results/day4/` contains the machine-readable record.

## Known methodological limitations

- Corpus coverage is intentionally small and topic-biased.
- Only 25 cases represent authored natural-language questions.
- Relevance judgements are sparse and were not independently clinician-adjudicated.
- The deterministic RAG checks verify provenance, not medical correctness.
- Timing came from one Windows CPU workstation and is not a service-level guarantee.
- The source catalog has no automated refresh job, so updates require a deliberate new
  version, checksum, validation, and regression run.
