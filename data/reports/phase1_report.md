# Phase 1 Baseline Report

## Source Summary

- Provider: `gemini`
- Model: `gemini-2.5-flash`
- Source API: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`

## Metrics

| Metric | Value |
| :--- | :--- |
| Records | 24 |
| Test samples | 10 |
| Vector collection | `papers-baseline` |
| Retrieval hit rate | 1.000 |
| Mean token F1 | 0.771 |
| Judge accuracy | 0.800 |
| Mean judge score | 4.000 |
| Quality success | True |
| Fresh | True |
| Stale rows | 1 |
| Stale ratio | 0.0417 |

## Data Quality

{
  "success": true,
  "expectation_count": 6,
  "statistics": {
    "evaluated_expectations": 6,
    "successful_expectations": 6,
    "unsuccessful_expectations": 0,
    "success_percent": 100.0
  },
  "freshness": {
    "latest_published": "2026-07-22",
    "oldest_published": "2026-03-28",
    "stale_rows": 1,
    "total_rows": 24,
    "stale_ratio": 0.0417,
    "threshold_days": 180,
    "allowed_stale_ratio": 0.25,
    "is_fresh": true
  }
}

