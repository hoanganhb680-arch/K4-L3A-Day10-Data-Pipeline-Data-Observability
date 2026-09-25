from __future__ import annotations

from typing import Any

from core.utils import write_text


METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _value(payload: dict[str, Any], key: str, default="—"):
    return payload.get(key, default)


def _status(payload: dict[str, Any]) -> str:
    return "PASS" if payload.get("success", payload.get("is_fresh", False)) else "FAIL"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a report from the supplied runtime payloads only."""
    text = f"""# Phase 1 — Baseline Data Pipeline

## Dataset and configuration

| Field | Value |
|---|---:|
| Dataset size | {_value(source_summary, 'dataset_size')} |
| Source | {_value(source_summary, 'source')} |
| Embedding model | {_value(source_summary, 'embedding_model')} |
| Collection | {_value(source_summary, 'collection')} |
| Test set size | {_value(source_summary, 'test_set_size')} |
| LLM provider | {_value(source_summary, 'llm_provider')} |
| Reference date (UTC) | {_value(source_summary, 'run_date')} |
| Source refresh requested | {_value(source_summary, 'refresh_source')} |
| Retrieval top_k | {_value(metrics, 'top_k')} |
| Test set SHA-256 | `{_value(metrics, 'test_set_sha256')}` |
| Heuristic judge samples | {_value(metrics, 'heuristic_judge_samples')} |
| RAGAS | {_value(metrics, 'ragas')} |

## Validation and evaluation

| Metric | Value |
|---|---:|
| Quality status | {_status(quality)} |
| Freshness status | {_status(freshness)} |
| Retrieval hit rate | {_value(metrics, 'retrieval_hit_rate')} |
| Mean token F1 | {_value(metrics, 'mean_token_f1')} |
| Judge accuracy | {_value(metrics, 'judge_accuracy')} |
| Mean judge score | {_value(metrics, 'mean_judge_score')} |

Quality evaluated {quality.get('evaluated_expectations', '—')} expectations and failed {quality.get('failed_expectations', '—')}.
Freshness observed {_value(freshness, 'stale_rows')} stale rows out of {_value(freshness, 'total_rows')} (ratio {_value(freshness, 'stale_ratio')}) with threshold {_value(freshness, 'threshold_days')} days.

## Artifacts

{chr(10).join(f"- `{path}`" for path in source_summary.get('artifact_paths', []))}

## Interpretation

The baseline numbers are measurements from the preserved local response and fixed evaluation set.
QA uses MiniLM cosine retrieval plus an exact-title lookup and extracts the requested metadata or first summary sentence.
Token F1 uses sets of lowercase whitespace-separated tokens, as defined by the starter code.
The heuristic judge count above records how many answers used Token F1 thresholds instead of an external LLM judge (all answers in mock mode).
This benchmark measures corpus integrity and the starter QA path; it is not a pure semantic-search or generative-answer benchmark.
Baseline quality is {_status(quality)} and freshness is {_status(freshness)}; a freshness alert is retained even if the data passes structural quality checks.
"""
    write_text(report_path, text)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a three-state comparison using the generated artifacts."""
    table = "\n".join(f"| `{name}` | {baseline_metrics[name]:.6f} | {corrupted_metrics[name]:.6f} | {repaired_metrics[name]:.6f} |"
                      for name in METRICS)
    table += f"\n| Quality status | {baseline_metrics['quality_status']} | {_status(corrupted_quality)} | {_status(repaired_quality)} |"
    table += f"\n| Freshness status | {baseline_metrics['freshness_status']} | {_status(corrupted_freshness)} | {_status(repaired_freshness)} |"
    deltas = "\n".join(f"- `{name}`: corruption minus baseline = {corrupted_metrics[name] - baseline_metrics[name]:+.6f}; "
                       f"repair minus baseline = {repaired_metrics[name] - baseline_metrics[name]:+.6f}."
                       for name in METRICS)
    failures = ", ".join(f"{item['expectation']}({item['column']})" for item in corrupted_quality['results'] if not item['success'])
    text = f"""# Corruption and Repair Comparison

The same deterministic evaluation set is used for all three states. SHA-256: `{baseline_metrics['test_set_sha256']}`.
Provider: `{baseline_metrics['llm_provider']}`; heuristic judge samples: {baseline_metrics['heuristic_judge_samples']} baseline, {corrupted_metrics['heuristic_judge_samples']} corrupted, {repaired_metrics['heuristic_judge_samples']} repaired.

| Metric / signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
{table}

## Measured changes

{deltas}

Failed corrupted checks: {failures or 'none'}.
Corrupted freshness: {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']} stale ({corrupted_freshness['stale_ratio']:.2%}).
Repaired freshness: {repaired_freshness['stale_rows']}/{repaired_freshness['total_rows']} stale ({repaired_freshness['stale_ratio']:.2%}).
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
"""
    write_text(report_path, text)
