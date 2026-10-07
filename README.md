# IrishClinicalRAG

**Evidence-grounded clinical and biomedical research assistance for Irish healthcare guidance.**

Hybrid retrieval · Irish evidence provenance · Reranking-ready · Safety-aware · FastAPI · Docker-ready

> Early development release. This is a research and educational decision-support
> project, not a certified medical device and not a replacement for clinical judgement.

IrishClinicalRAG is retrieval-first: every medically meaningful answer should be
traceable to authoritative evidence, with source organisation, document title,
date, URL, retrieved passage, score, and evidence-sufficiency information.

## Current milestone

Day 1 establishes a complete local evidence path:

```text
official Irish source -> immutable download -> parse -> section-aware chunk
-> metadata validation -> BM25 + dense vectors -> RRF hybrid retrieval
```

The baseline dense retriever uses deterministic hashed vectors so the pipeline is
fully reproducible without model downloads. A SentenceTransformer backend is a
planned drop-in experiment, not a hidden prerequisite.

## Quick start

Python 3.11–3.13 is recommended. Python 3.14 support depends on upstream wheels.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
irishclinicalrag ingest configs/sources.json
irishclinicalrag retrieve "What principles guide antimicrobial prescribing?"
pytest
```

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
append-only manifest under `data/manifests/`.

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
