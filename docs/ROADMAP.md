# Roadmap

The seven-day release freezes major architecture changes. Remaining work is ordered by
release risk and recruiter/PI value. Each item below is written so it can become a GitHub
issue without inventing scope.

## P0 — Close release acceptance gaps

### Activate and verify the local Windows Docker runtime

**Why:** the image is CI-built, but the workstation has not executed the full Compose
path because WSL 2 platform support is not active.

**Acceptance:**

1. From Administrator CMD, run `wsl --install --no-distribution` and restart Windows.
2. Confirm `wsl --status` no longer reports the Virtual Machine Platform error.
3. Run `docker version` and confirm both client and server sections respond.
4. Run `docker compose up --build -d` from the repository root.
5. Wait for `docker compose ps` to report the service healthy.
6. Confirm `/health`, one grounded query, one abstention, and one emergency bypass.
7. Record the exact commands and result in `docs/STATUS.md`, then run
   `docker compose down` without deleting the named data volume.

### Publish a controlled research demo

**Why:** a public demo is the remaining strict charter definition-of-done item.

**Acceptance:**

- deploy the exact Git revision using the production Docker image;
- preserve the research-only, no-patient-data, and emergency notices;
- use HTTPS and runtime secrets only;
- pass liveness/readiness and grounded/abstention/emergency smoke tests;
- set practical request, memory, and concurrency limits;
- document URL, revision, hosting boundary, and rollback procedure;
- do not claim clinical validation or production medical suitability.

## P1 — Strengthen research validity

### Independent clinical review

Have qualified reviewers assess a preregistered question subset for source relevance,
answer correctness, completeness, harmful omission, abstention appropriateness, and
inter-rater agreement. Keep this separate from deterministic provenance metrics.

### Expand natural-question evaluation

Increase the authored reviewed cohort across additional Irish guidance topics, add hard
negative and ambiguous questions, and report confidence intervals. Keep lexical probes as
a separate engineering cohort.

### Calibrate evidence sufficiency

Review supported and abstained cases, especially `curated-021`, then choose thresholds on
a development split and report once on a held-out split. Optimise for safe abstention, not
answer volume.

### Decide the reranker deployment policy

Benchmark CPU and GPU latency under realistic concurrency. Compare always-on reranking,
conditional reranking, and hybrid-only service modes. Preserve independent evaluation and
explicit fallback behavior.

## P1 — Keep sources current

Create a scheduled, review-gated source monitor that detects authoritative document
changes, downloads checksum-addressed candidates, and opens a proposed corpus-lock update.
Never silently replace the active corpus. Require integrity checks and evaluation
regression before promotion.

## P2 — Product and operations

- Add query routing only if evaluation shows a measurable benefit.
- Export privacy-safe aggregate metrics to an operational dashboard.
- Add rate limiting and abuse controls for a public demo.
- Consider more parsers only when a selected authoritative source requires them.

## Explicitly deferred

GraphRAG, FHIR integration, medical model fine-tuning, large-scale PubMed ingestion,
multimodal imaging, and broad agentic web search remain outside the release. They should
not begin until public deployment, clinical review, refresh governance, and evaluation
coverage are stronger.
