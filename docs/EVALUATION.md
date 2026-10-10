# Evaluation protocol

The Day 4 benchmark separates evidence retrieval from answer generation. It is intended
to make architectural comparisons reproducible; it does not establish clinical validity.

## Dataset

`data/eval/questions.jsonl` contains 100 synthetic, non-patient cases:

- 25 manually authored questions checked against specific passages in the locked Irish
  guidance corpus (`cohort=curated`)
- 75 deterministic lexical probes derived from individual source chunks
  (`cohort=synthetic_probe`)

The easier probe cohort checks indexing and provenance plumbing but can overstate
real-world performance. For that reason, every experiment reports the 25-question
curated cohort separately. Relevance labels are deliberately transparent and may be
incomplete where multiple passages could answer a question.

Regenerate the combined dataset after a corpus change:

```bash
irishclinicalrag build-eval
```

The build fails if the reviewed labels no longer exist, if the curated seed does not
contain exactly 25 cases, or if the final dataset is not exactly 100 unique cases.

## Retrieval matrix and metrics

The required comparison runs the same questions through:

1. BM25
2. BGE dense retrieval
3. reciprocal-rank-fusion hybrid retrieval
4. hybrid retrieval followed by a cross-encoder reranker

For each method and cohort, the runner records Precision@5, Recall@5, Hit Rate@5, MRR,
nDCG@5, source-level equivalents, and latency. Chunk relevance and source-document
relevance are measured separately. Each method receives one unmeasured warm-up query so
model loading does not distort per-query mean, median, or p95 latency.

```bash
irishclinicalrag evaluate --output-dir experiments/results/day4
```

Each run writes:

- `metrics.json`: configuration, model names, dataset checksum, corpus fingerprint,
  timestamp, Git commit, aggregate metrics, and limitations
- `predictions.jsonl`: per-question ranked chunk IDs, document IDs, scores, and latency
- `comparison.md`: concise comparison table for the curated and full cohorts

## Grounded-answer checks

The default extractive answer path is assessed only on the curated cohort. The runner
records evidence sufficiency, exact citation provenance, answer citation completeness,
extractive faithfulness, expected-source citation, and reference token overlap.

These deterministic checks are useful regression signals. They are not a substitute for
clinical review, and reference token overlap is not a clinical correctness score. No
LLM-as-judge result is represented as ground truth.

## Reproducibility and safety

The benchmark uses only public clinical documents and synthetic questions. It contains no
patient data. Raw documents, generated corpus passages, vector files, and model weights
remain untracked; the experiment binds results to their dataset checksum and corpus
fingerprint. Retrieval still functions without a generation provider.
