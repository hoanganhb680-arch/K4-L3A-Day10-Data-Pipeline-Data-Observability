# Corruption and Repair Comparison

The same deterministic evaluation set is used for all three states. SHA-256: `08ed9447c4687393b2023c0a2ae8ee8f8ed5dbdaeea764706585732e302321f6`.
Provider: `mock`; heuristic judge samples: 10 baseline, 10 corrupted, 10 repaired.

| Metric / signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| `retrieval_hit_rate` | 1.000000 | 0.700000 | 1.000000 |
| `mean_token_f1` | 1.000000 | 0.600000 | 1.000000 |
| `judge_accuracy` | 1.000000 | 0.600000 | 1.000000 |
| `mean_judge_score` | 5.000000 | 3.400000 | 5.000000 |
| Quality status | PASS | FAIL | PASS |
| Freshness status | PASS | FAIL | PASS |

## Measured changes

- `retrieval_hit_rate`: corruption minus baseline = -0.300000; repair minus baseline = +0.000000.
- `mean_token_f1`: corruption minus baseline = -0.400000; repair minus baseline = +0.000000.
- `judge_accuracy`: corruption minus baseline = -0.400000; repair minus baseline = +0.000000.
- `mean_judge_score`: corruption minus baseline = -1.600000; repair minus baseline = +0.000000.

Failed corrupted checks: expect_column_values_to_be_unique(paper_id), expect_column_value_lengths_to_be_between(summary), expect_column_value_lengths_to_be_between(title).
Corrupted freshness: 10/21 stale (47.62%).
Repaired freshness: 1/24 stale (4.17%).
Baseline freshness details remain in `data/quality/freshness_report.json`.

## Evidence chain

- The corruption suite records six deterministic scenarios in `data/results/corruption_log.json`. Quality failures and stale-date changes are computed from the corrupted dataframe; they are not forced by a constant status.
- Repair reloads `data/raw/crossref_records.json`, rebuilds the clean schema, and re-indexes it in `papers-repaired`, so the repaired results are independent of the corrupted dataframe.
- A metric that remains unchanged is reported as measured: the exact-title lookup in the QA layer can preserve retrieval for some benchmark questions even when other records are damaged.
- This is a combined corruption experiment. Per-scenario causal attribution requires separate ablation runs; answer-level changes can be inspected in `data/results/*_answers.json`.
- Corrupted data is indexed solely in the isolated `papers-corrupted` collection for this lab's impact measurement. The baseline and repaired quality gates reject invalid data before indexing.

## Artifacts

- `data/clean/papers_clean.json`, `papers_clean_corrupted.json`, `papers_clean_repaired.json`
- `data/embeddings/papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json`
- `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` and matching answer files
- `data/quality/baseline_quality_report.json`, `corrupted_quality_report.json`, `repaired_quality_report.json`
- `data/quality/freshness_report.json`, `corrupted_freshness_report.json`, `repaired_freshness_report.json`
