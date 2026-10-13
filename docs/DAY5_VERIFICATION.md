# Day 5 product-layer verification

Date: 2026-10-13

## Delivered

- FastAPI continues to expose `/health`, `/query`, `/retrieve`, `/sources`, and
  `/metrics`, with retrieval independently callable from generation.
- The evidence interface displays safety status, confidence/evidence sufficiency,
  citation-used versus supporting passages, source metadata, rank, score, publication or
  update date, document version, topic, authoritative URL, and expandable method/model
  details.
- Loading, 90-second client timeout, API-error, retry, empty-evidence, abstention, and
  emergency states are explicit and keyboard-accessible.
- Privacy-safe structured JSON events cover request ID, route, input/output token counts,
  public document IDs, scores, methods/models, latency, outcome, and safety status. Raw
  questions, answers, and passages are not logged.
- In-memory metrics cover request types, retrieval/generation operations, errors,
  abstentions, emergency escalations, evidence counts, and retrieval/generation/total
  latency.

## Verification evidence

- `ruff check .`: passed.
- `pytest --cov=irishclinicalrag --cov-report=term-missing`: 39 passed; 79% statement
  coverage.
- FastAPI contract tests cover normal retrieval, grounded/abstaining query behavior,
  emergency bypass, failed retrieval metrics, and structured-log privacy.
- Browser-tested against the real 692-chunk local corpus at desktop size and at a
  390 x 844 mobile viewport.
- Browser flows verified a citation-verified grounded response, an emergency escalation
  with retrieval skipped, and an insufficient-evidence abstention.
- The browser console reported no errors or warnings during the grounded flow.

## Known limitations

- The interface is a research and educational tool, not a certified medical device.
- The corpus is intentionally scoped and can become stale; users must verify linked
  source guidance.
- The default generator is a deterministic extractive baseline. It is auditable but not
  intended to provide polished clinical prose.
- CPU reranker cold start remains noticeably slower than warm requests; latency and
  caching work remain part of Day 6.
- The test suite reports one upstream Starlette `TestClient`/httpx deprecation warning.
