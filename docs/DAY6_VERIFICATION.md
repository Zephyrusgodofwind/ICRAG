# Day 6 deployment and reliability verification

Completed: 2026-10-14

## Delivered

- Added a single-entry, file-signature-aware runtime cache for public corpus data,
  configuration, BM25, dense-index, fusion, and reranker adapters. It invalidates when
  the config, chunks, or dense-index files change.
- Raw questions, answers, and query results are not cached.
- Added optional startup model warming (`IRISHCLINICALRAG_WARM_MODELS=1`) so model load
  occurs before readiness rather than during the first user query.
- Split process liveness (`/health/live`) from corpus/retrieval readiness (`/health`), with
  the readiness endpoint failing closed using HTTP 503.
- Added explicit hybrid fallback when the reranker model is unavailable and grounded
  extractive fallback when a remote generator fails or is misconfigured.
- Added cache hit/miss fields to retrieval metadata, privacy-safe query events, aggregate
  metrics, and the UI method details.
- Hardened the container as non-root with a read-only root filesystem, writable data
  volume and temporary filesystem, dropped capabilities, no-new-privileges, PID limit,
  graceful shutdown, configurable paths/host/port/logging, and a five-minute first-start
  health grace period.
- Added a GitHub Actions production-image build because Docker is not installed on the
  local development machine. The production image built successfully in remote CI.

## Verification evidence

- `ruff check .`: passed.
- `node --check frontend/app.js`: passed.
- `pytest --cov=irishclinicalrag --cov-report=term-missing`: 49 passed; 80% statement
  coverage.
- Real API readiness check against the 692-chunk corpus: ready, eight documents,
  semantic index available, component cache generation 1.
- With model warming enabled, the first ready-state grounded request completed in
  1,936.1 ms end to end (1,837.4 ms retrieval); the next completed in 1,636.9 ms
  (1,625.9 ms retrieval). Both were component-cache hits and returned `grounded`.
- Aggregate metrics after those checks reported two requests, two cache hits, no errors,
  five evidence passages per request, 1,731.643 ms mean retrieval latency, and
  1,737.741 ms mean total latency.

These timings are local CPU engineering measurements, not service-level guarantees. Model
warming moves one-time model loading into startup; it does not remove that startup cost.

## Full evaluation regression

The complete committed 100-case dataset was rerun locally across BM25, dense, hybrid,
and hybrid-plus-reranker retrieval (400 predictions total):

| Method | Reviewed Recall@5 | Reviewed MRR | Median warm latency |
|---|---:|---:|---:|
| BM25 | 0.820 | 0.641 | 2.6 ms |
| Dense | 0.780 | 0.660 | 61.7 ms |
| Hybrid | 0.920 | 0.827 | 66.0 ms |
| Hybrid + reranker | 0.940 | 0.837 | 1,639.4 ms |

All 400 retrieved chunk rankings matched the committed Day 4 predictions exactly. RAG
checks completed and the corpus fingerprint remained
`6a92d8f3b1b30c1fecb3263c1043e08be5248f06daa1eab64d3610c08f08dae1`.
The regression outputs are local ignored artifacts; Day 4 remains the canonical committed
benchmark because retrieval quality did not change.

## Constraints and remaining work

- Docker is not installed on this machine, so no local Compose-runtime claim is made.
  Static deployment tests pass and the GitHub Actions production image build completed
  successfully in [CI run 38374542771](https://github.com/Zephyrusgodofwind/ICRAG/actions/runs/38374542771).
- No public deployment was attempted because no hosting target or deployment credentials
  are configured. This is recorded rather than presenting a local service as public.
- One upstream Starlette `TestClient`/httpx deprecation warning remains.
- RunPod was not required; the full regression completed locally on CPU.
