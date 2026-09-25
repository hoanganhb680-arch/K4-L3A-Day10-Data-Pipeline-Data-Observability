# Phase 1 — Baseline Data Pipeline

## Dataset and configuration

| Field | Value |
|---|---:|
| Dataset size | 24 |
| Source | Crossref REST API format; preserved local response |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Collection | papers-baseline |
| Test set size | 10 |
| LLM provider | mock |
| Reference date (UTC) | 2026-09-25 |
| Source refresh requested | False |
| Retrieval top_k | 4 |
| Test set SHA-256 | `08ed9447c4687393b2023c0a2ae8ee8f8ed5dbdaeea764706585732e302321f6` |
| Heuristic judge samples | 10 |
| RAGAS | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

## Validation and evaluation

| Metric | Value |
|---|---:|
| Quality status | PASS |
| Freshness status | PASS |
| Retrieval hit rate | 1.0 |
| Mean token F1 | 1.0 |
| Judge accuracy | 1.0 |
| Mean judge score | 5 |

Quality evaluated 12 expectations and failed 0.
Freshness observed 1 stale rows out of 24 (ratio 0.041666666666666664) with threshold 180 days.

## Artifacts

- `data\raw\crossref_response.json`
- `data\raw\crossref_records.json`
- `data\clean\papers_clean.csv`
- `data\clean\papers_clean.json`
- `data\embeddings\papers_embeddings.json`
- `data\eval\test_set.json`
- `data\results\baseline_metrics.json`
- `data\results\baseline_answers.json`
- `data\quality\baseline_quality_report.json`
- `data\quality\freshness_report.json`
- `data\reports\phase1_report.md`

## Interpretation

The baseline numbers are measurements from the preserved local response and fixed evaluation set.
QA uses MiniLM cosine retrieval plus an exact-title lookup and extracts the requested metadata or first summary sentence.
Token F1 uses sets of lowercase whitespace-separated tokens, as defined by the starter code.
The heuristic judge count above records how many answers used Token F1 thresholds instead of an external LLM judge (all answers in mock mode).
This benchmark measures corpus integrity and the starter QA path; it is not a pure semantic-search or generative-answer benchmark.
Baseline quality is PASS and freshness is PASS; a freshness alert is retained even if the data passes structural quality checks.
