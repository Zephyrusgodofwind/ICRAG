# Day 7 research-release verification

Completed: 2026-10-14

## Release outcomes

- Reworked the README into a recruiter/PI-facing release document covering motivation,
  demo, sources, methodology, measured results, safety, installation, deployment,
  limitations, roadmap, and attribution.
- Added a detailed methodology page, portfolio/CV narrative, prioritised issue-ready
  roadmap, request-flow diagram, and three original product screenshots.
- Added release-contract tests that keep required documentation/screenshots present and
  ensure README headline metrics match the committed experiment record.
- Made no risky architecture or model changes after the Day 6 freeze.

## Final experiment evidence

Day 6 reran the complete 100-case benchmark across four independently selectable methods
(400 predictions). Every retrieved chunk ranking matched the committed Day 4 canonical
run, so Day 7 retains those measured results instead of manufacturing a new experiment:

| Method | Reviewed Recall@5 | Reviewed MRR | Canonical median warm latency |
|---|---:|---:|---:|
| BM25 | 0.820 | 0.641 | 2.6 ms |
| Dense | 0.780 | 0.660 | 57.8 ms |
| Hybrid | 0.920 | 0.827 | 68.3 ms |
| Hybrid + reranker | 0.940 | 0.837 | 1,698.6 ms |

The dataset has 25 manually authored/source-checked cases and 75 deterministic lexical
probes. These are engineering results on synthetic questions, not clinical validation.

## Real browser acceptance

The final service was started with model warming against the 692-chunk/eight-document
corpus. `/health` reported ready, the semantic index loaded, and the public-component cache
reported a hit.

The actual interface, not a static file preview, passed these checks:

1. `How should antimicrobial prescriptions be reviewed?` returned a grounded answer,
   `Citation verified`, 77% evidence confidence, five evidence passages, exact source
   links, ranks, scores, pages, and citation-use labels.
2. `zzzxxyy unmatched question` returned `Abstained safely` and `Evidence insufficient`.
3. `I have chest pain and cannot breathe` returned emergency guidance, zero evidence
   passages, and `skipped-emergency-safety` retrieval.
4. The 390 × 844 mobile viewport had no horizontal overflow; question and search controls
   remained available.
5. The browser console contained zero errors during the audited flows.

Screenshots are committed under `docs/assets/`. They contain only synthetic questions and
public-source content.

## Automated quality gates

- `ruff check .`: passed.
- `pytest`: 51 passed.
- `node --check frontend/app.js`: passed.
- YAML parsing for Compose and GitHub Actions configuration: passed.
- GitHub Actions production-image build: passed in
  [run 38374542771](https://github.com/Zephyrusgodofwind/ICRAG/actions/runs/38374542771).

One upstream Starlette `TestClient`/httpx deprecation warning remains and does not indicate
an application test failure.

## Docker and deployment boundary

Docker Desktop 29.8.2 and Compose 5.6.0 are installed, and the production image has been
built by GitHub Actions. Local engine verification is currently blocked because Windows
reports that the WSL 2 Virtual Machine Platform requirement is not active in this session.
An administrator must run `wsl --install --no-distribution`, restart Windows, and then run
the local Compose acceptance sequence in `docs/ROADMAP.md`.

No public hosting target or deployment credential is configured, so this repository does
not claim a live public demo. The deadline plan explicitly permits public deployment to be
cut before any non-negotiable evidence, evaluation, reproducibility, or documentation
work. Public hosting remains the final definition-of-done gap.

## Release assessment

All non-negotiable product components and portfolio artifacts in the charter are
implemented: authoritative corpus, repeatable ingestion, metadata-aware chunking, four
retrieval paths, grounded generation, citation verification, safety, evaluation, measured
results, API, usable UI, hardened Docker specification, documentation, diagrams,
screenshots, and critical tests.

The core seven-day research release is therefore substantially complete and ready for
repository review. It is not labelled fully complete under the charter's strict final
definition because a recruiter cannot yet open a live public deployment and local Compose
runtime acceptance is pending the Windows platform activation/restart.
