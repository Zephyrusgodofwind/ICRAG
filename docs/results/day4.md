# Day 4 evaluation results

- Run date: 2026-10-13
- Experiment code commit: `a704bb17fc05b41e7dd856cc10de732752cb7433`
- Corpus fingerprint: `6a92d8f3b1b30c1fecb3263c1043e08be5248f06daa1eab64d3610c08f08dae1`
- Dataset: 100 synthetic, non-patient questions (25 curated + 75 lexical probes)
- Dense model: `BAAI/bge-small-en-v1.5`
- Reranker: `cross-encoder/ms-marco-MiniLM-L6-v2`

The machine-readable result and all 400 per-case predictions are committed under
`experiments/results/day4/`. This report interprets the measured results without claiming
clinical validation.

## Reviewed-question retrieval results

| Method | Precision@5 | Recall@5 | Hit Rate@5 | MRR | nDCG@5 | Source Recall@5 | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 0.216 | 0.820 | 0.840 | 0.641 | 0.686 | 1.000 | 2.3 ms |
| Dense | 0.208 | 0.780 | 0.800 | 0.660 | 0.691 | 1.000 | 58.3 ms |
| Hybrid | 0.248 | 0.920 | 0.920 | 0.827 | 0.852 | 1.000 | 58.8 ms |
| Hybrid + reranker | 0.256 | 0.940 | 0.960 | 0.837 | 0.858 | 1.000 | 1,679.4 ms |

Latency is warm CPU query latency after one unmeasured warm-up query per method. It does
not include model loading. Exact mean, median, p95, full-cohort, and probe-cohort values
are retained in `metrics.json`.

## Findings

- Hybrid retrieval was stronger than either single retriever on the 25 reviewed questions:
  Recall@5 was 0.920 versus 0.820 for BM25 and 0.780 for dense retrieval. MRR was 0.827
  versus 0.641 and 0.660 respectively.
- Cross-encoder reranking made a smaller improvement over hybrid: +0.020 Recall@5 and
  +0.010 MRR, while median latency increased from 58.8 ms to 1,679.4 ms (about 28.6 times).
  Whether that trade-off is appropriate depends on the deployment latency budget.
- All four methods achieved source-document Recall@5 of 1.000 on the curated cohort. The
  remaining failures were therefore exact-passage ranking failures rather than complete
  source-document failures.
- BM25 performed best on the deliberately lexical probe cohort. This is expected because
  those probes were generated from rare terms in a labelled passage. The probe results
  verify indexing and provenance plumbing; they are not a substitute for the curated
  cohort and should not be used as the headline quality result.
- Reranking reduced full-dataset Recall@5 from 0.930 to 0.855 by demoting some exact-term
  probe passages. This shows that the general-purpose MS MARCO reranker is not uniformly
  beneficial across query types.

These observations support the limited conclusion that hybrid retrieval performed best
among the non-reranked configurations on this dataset, while the reranker provided a
modest reviewed-question gain at a large CPU-latency cost. The sample is too small to
claim statistical or clinical superiority.

## Curated failure audit

For hybrid plus reranking:

- `curated-022` (standard precautions and blood/body substances) missed the labelled
  exact chunk, although other passages from the correct NCEC document were retrieved.
- `curated-001` (good antimicrobial-stewardship prescribing practices) retrieved one of
  two labelled overlapping chunks at rank 4, so it was a partial relevance-label hit.

The deterministic grounded-answer checks abstained on `curated-021` (future beta-lactam
precautions after penicillin anaphylaxis) because the evidence-sufficiency policy did not
reach its threshold. This is a conservative failure, not a claim that no relevant source
was retrieved, and it should inform later safety-threshold calibration.

## Grounded-answer regression checks

The offline extractive baseline was evaluated on the 25 reviewed questions only:

| Check | Result |
|---|---:|
| Evidence sufficient | 0.960 |
| Citation correctness | 0.960 |
| Citation completeness | 0.960 |
| Extractive faithfulness | 0.960 |
| Expected source cited | 0.960 |
| Reference token F1 | 0.237 |

The first five values reflect 24 of 25 cases. Reference token F1 is low because the
extractive answer is not written to match the manually authored reference wording; it is
reported as a regression signal, not a medical correctness score.

## Limitations

- The curated subset was source-checked but not independently scored by clinicians for
  medical correctness, completeness, or safety.
- Relevance labels are sparse. Other passages can be clinically relevant without being
  listed as exact expected chunks.
- The 75 lexical probes are easier and structurally different from natural questions.
- No LLM judge was used. The RAG checks are deterministic provenance and overlap checks,
  not proof of answer correctness.
- Latency was measured on one local Windows CPU environment and should not be generalised
  to hosted or GPU deployment.
- The corpus is intentionally small and does not represent complete Irish clinical
  guidance coverage.
