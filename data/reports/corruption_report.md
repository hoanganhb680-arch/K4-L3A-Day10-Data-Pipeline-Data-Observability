# Corruption Impact Report

## Performance Comparison

| Metric | Baseline | Corrupted | Repaired |
| :--- | ---: | ---: | ---: |
| Retrieval hit rate | 1.000 | 0.800 | 1.000 |
| Mean token F1 | 0.771 | 0.559 | 0.771 |
| Judge accuracy | 0.800 | 0.600 | 0.800 |
| Mean judge score | 4.000 | 3.200 | 4.000 |

## Quality Gates

| State | Quality success | Fresh | Stale ratio |
| :--- | ---: | ---: | ---: |
| Corrupted | False | False | 0.3043 |
| Repaired | True | True | 0.0417 |

## Detailed Artifacts

```text
Baseline metrics = read_json('data/results/baseline_metrics.json')
Corrupted metrics = read_json('data/results/corrupted_metrics.json')
Repaired metrics  = read_json('data/results/repaired_metrics.json')
```

