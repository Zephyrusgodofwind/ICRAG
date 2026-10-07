# IrishClinicalRAG

**Evidence-grounded clinical and biomedical research assistance for Irish healthcare guidance.**

Hybrid retrieval · Irish evidence provenance · Reranking-ready · Safety-aware · FastAPI · Docker-ready

> Early development release. This is a research and educational decision-support
> project, not a certified medical device and not a replacement for clinical judgement.

IrishClinicalRAG is retrieval-first: every medically meaningful answer should be
traceable to authoritative evidence, with source organisation, document title,
date, URL, retrieved passage, score, and evidence-sufficiency information.

## Current milestone

Day 2 establishes a validated, multi-topic Irish evidence path:

```text
official Irish source -> immutable download -> parse -> section-aware chunk
-> corpus integrity gate -> BM25 + BGE semantic vectors -> RRF hybrid retrieval
```

The current catalog contains eight public HSE/NCEC documents and produces 692
checksum-verified passages. A persistent `BAAI/bge-small-en-v1.5` index is used when
available; the deterministic hashing backend remains an offline fallback. BM25, dense,
and hybrid retrieval can each be run and inspected independently. These are corpus and
engineering counts, not retrieval-quality evaluation results.

## Quick start

Python 3.11 or newer is required.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,ml]"
irishclinicalrag ingest configs/sources.json
irishclinicalrag validate configs/sources.json
irishclinicalrag build-index
irishclinicalrag retrieve "What principles guide antimicrobial prescribing?" --method hybrid --debug
pytest
```

Use `--method bm25`, `--method dense`, or `--method hybrid` to inspect each retrieval
path. Model-backed dense retrieval loads the already-downloaded model locally at query
time; it does not require Hugging Face network access after the index is built.

Start the API and web interface at `http://localhost:8000`:

```bash
.venv/Scripts/uvicorn irishclinicalrag.api.app:app --reload
```

Or build, ingest the configured source when needed, and start everything with:

```bash
docker compose up --build
```

The committed source catalog contains authoritative URLs, not copied clinical
content. Downloads are checksum-addressed under `data/raw/` and recorded in an
append-only manifest under `data/manifests/`. Generated raw files, passages, and vector
artifacts are ignored by Git; the committed corpus lock records exact checksums, counts,
versions, URLs, and the corpus fingerprint needed to reproduce the snapshot.

## Architecture

See [docs/architecture/system.md](docs/architecture/system.md) and the project
charter in [IrishClinicalRAG_PROJECT_PLAN.md](IrishClinicalRAG_PROJECT_PLAN.md).

Required API endpoints are available at `/health`, `/query`, `/retrieve`,
`/sources`, and `/metrics`; OpenAPI documentation is at `/docs`.

## Safety and privacy

- Weak or missing evidence must produce abstention, not confident medical advice.
- Obvious emergency language is escalated to urgent real-world help.
- Generation must be restricted to retrieved evidence and expose limitations.
- Only public documents and synthetic/demo questions belong in this repository.
- Do not enter patient-identifiable or private medical information.

## Status

See [docs/STATUS.md](docs/STATUS.md) for the charter checklist and measured status.
Metrics will be published only after the benchmark has run; no result is invented.

## Attribution

This repository is independently implemented. See [ATTRIBUTION.md](ATTRIBUTION.md)
for architectural influences and source-document ownership.
