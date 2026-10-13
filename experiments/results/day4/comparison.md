# Day 4 retrieval comparison

Metrics are measured on the committed dataset. See `metrics.json` for full precision, source-recall, latency, cohort, model, and limitation details.

| Method | Cohort | Recall@5 | MRR | nDCG@5 | Source recall@5 | Median latency (ms) |
|---|---:|---:|---:|---:|---:|---:|
| bm25 | curated | 0.820 | 0.641 | 0.686 | 1.000 | 2.6 |
| bm25 | all | 0.955 | 0.812 | 0.849 | 1.000 | 2.4 |
| dense | curated | 0.780 | 0.660 | 0.691 | 1.000 | 57.8 |
| dense | all | 0.495 | 0.390 | 0.417 | 0.790 | 57.2 |
| hybrid | curated | 0.920 | 0.827 | 0.852 | 1.000 | 68.3 |
| hybrid | all | 0.930 | 0.666 | 0.732 | 0.990 | 62.3 |
| hybrid-rerank | curated | 0.940 | 0.837 | 0.858 | 1.000 | 1698.6 |
| hybrid-rerank | all | 0.855 | 0.680 | 0.723 | 0.980 | 1648.2 |

These results do not establish clinical validity or medical correctness.
