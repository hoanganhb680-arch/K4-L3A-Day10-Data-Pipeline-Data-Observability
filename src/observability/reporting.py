from __future__ import annotations

from typing import Any


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """viet markdown report cho baseline phase."""
    content = f"""# Phase 1: Baseline RAG Pipeline Report

## Source Data Summary
- Raw Records: {source_summary.get('raw_count', 0)}
- Cleaned Records: {source_summary.get('clean_count', 0)}

## Evaluation Metrics
- Number of Samples: {metrics.get('samples', 0)}
- Retrieval Hit Rate: {metrics.get('retrieval_hit_rate', 0.0):.2f}
- Mean Token F1 Score: {metrics.get('mean_token_f1', 0.0):.2f}
- Judge Accuracy: {metrics.get('judge_accuracy', 0.0):.2f}
- Mean Judge Score: {metrics.get('mean_judge_score', 0.0):.2f}

## Data Quality Checks
- Success: {quality.get('success', False)}
- Evaluated Expectations: {quality.get('statistics', {}).get('evaluated_expectations', 0)}
- Successful Expectations: {quality.get('statistics', {}).get('successful_expectations', 0)}

## Freshness Report
- Total Rows: {freshness.get('total_rows', 0)}
- Stale Rows: {freshness.get('stale_rows', 0)}
- Is Fresh: {freshness.get('is_fresh', False)}
- Latest Published: {freshness.get('latest_published', 'N/A')}
- Oldest Published: {freshness.get('oldest_published', 'N/A')}
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


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
    """viet markdown report so sanh baseline/corrupted/repaired."""
    content = f"""# Phase 2: Corruption and Repair Comparison Report

## Evaluation Metrics Comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Retrieval Hit Rate | {baseline_metrics.get('retrieval_hit_rate', 0.0):.2f} | {corrupted_metrics.get('retrieval_hit_rate', 0.0):.2f} | {repaired_metrics.get('retrieval_hit_rate', 0.0):.2f} |
| Mean Token F1 Score | {baseline_metrics.get('mean_token_f1', 0.0):.2f} | {corrupted_metrics.get('mean_token_f1', 0.0):.2f} | {repaired_metrics.get('mean_token_f1', 0.0):.2f} |
| Judge Accuracy | {baseline_metrics.get('judge_accuracy', 0.0):.2f} | {corrupted_metrics.get('judge_accuracy', 0.0):.2f} | {repaired_metrics.get('judge_accuracy', 0.0):.2f} |
| Mean Judge Score | {baseline_metrics.get('mean_judge_score', 0.0):.2f} | {corrupted_metrics.get('mean_judge_score', 0.0):.2f} | {repaired_metrics.get('mean_judge_score', 0.0):.2f} |

## Data Quality Status
- **Corrupted**: Success={corrupted_quality.get('success', False)}
- **Repaired**: Success={repaired_quality.get('success', False)}

## Freshness Status
- **Corrupted**: Is Fresh={corrupted_freshness.get('is_fresh', False)} (Stale: {corrupted_freshness.get('stale_rows', 0)}/{corrupted_freshness.get('total_rows', 0)})
- **Repaired**: Is Fresh={repaired_freshness.get('is_fresh', False)} (Stale: {repaired_freshness.get('stale_rows', 0)}/{repaired_freshness.get('total_rows', 0)})
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
