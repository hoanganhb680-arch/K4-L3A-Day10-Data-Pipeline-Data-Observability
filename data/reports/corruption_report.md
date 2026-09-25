# Phase 2: Corruption and Repair Comparison Report

## Evaluation Metrics Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Retrieval Hit Rate | 1.00 | 0.80 | 1.00 |
| Mean Token F1 Score | 0.52 | 0.37 | 0.52 |
| Judge Accuracy | 0.50 | 0.40 | 0.50 |
| Mean Judge Score | 3.00 | 2.50 | 3.00 |

## Data Quality Status
- **Corrupted**: Success=False
- **Repaired**: Success=True

## Freshness Status
- **Corrupted**: Is Fresh=False (Stale: 23/23)
- **Repaired**: Is Fresh=True (Stale: 1/24)
