# Day 4 checkpoint history

Work was paused at the user's request on 2026-10-10 and resumed on 2026-10-13. The
latency-corrected benchmark subsequently completed and passed provenance validation.

## Durable state

- Commit `a7d145e` adds the reproducible 100-case dataset and evaluation framework.
- Commit `a704bb1` adds one unmeasured warm-up query per retrieval method so model startup
  does not distort query latency.
- The dataset contains 25 manually authored, source-checked questions and 75 unique,
  deterministic source probes. The dataset build and all relevance-label existence checks
  passed.
- Ruff passes. The test suite has 34 passing tests and 77.80% statement coverage.
- RunPod was not used; no credentials were requested and the available credit remains
  untouched.

## Resolved work

The interrupted command was rerun successfully:

```bash
.venv/Scripts/python -m irishclinicalrag.cli evaluate --output-dir experiments/results/day4
```

The final result contains 400 unique predictions and records commit `a704bb1`. It is
stored under `experiments/results/day4/`, with interpretation and failure analysis in
`docs/results/day4.md`.

The last fully completed pre-warm-up run is preserved locally under
`experiments/results/day4-pre-warmup/` and intentionally ignored by Git. It references
commit `a7d145e`. Its retrieval-quality values are useful only as a provisional
cross-check; its latency comparison is superseded by the warm-up protocol and must not be
published as the final Day 4 result. The validated warm-latency bundle supersedes it.

## Completed resume checklist

1. Ran the latency-corrected benchmark without changing the frozen dataset or labels.
2. Validated the dataset SHA, corpus fingerprint, 400 unique predictions, cohort counts,
   metric ranges, and recorded Git commit.
3. Audited curated misses and abstentions without relabelling cases to improve scores.
4. Wrote the measured interpretation and marked Day 4 complete after validation.
5. Run Ruff, tests, coverage, and corpus validation; inspect the staged diff for secrets,
   patient data, generated corpus blobs, and unrelated files.
6. Commit and push the final result bundle, then verify the GitHub remote accepted it.

Items 5 and 6 are the final repository closeout and are recorded in the Git history and
`docs/STATUS.md` once complete.
