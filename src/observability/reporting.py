from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a Markdown report for the clean-data baseline phase."""
    rows = [
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Records | {source_summary.get('records', '-')} |",
        f"| Test samples | {source_summary.get('test_samples', '-')} |",
        f"| Vector collection | `{source_summary.get('collection_name', '-')}` |",
        f"| Retrieval hit rate | {metrics.get('retrieval_hit_rate', 0):.3f} |",
        f"| Mean token F1 | {metrics.get('mean_token_f1', 0):.3f} |",
        f"| Judge accuracy | {metrics.get('judge_accuracy', 0):.3f} |",
        f"| Mean judge score | {metrics.get('mean_judge_score', 0):.3f} |",
        f"| Quality success | {bool(quality.get('success'))} |",
        f"| Fresh | {bool(freshness.get('is_fresh'))} |",
        f"| Stale rows | {freshness.get('stale_rows', '-')} |",
        f"| Stale ratio | {freshness.get('stale_ratio', '-')} |",
    ]

    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source Summary",
        "",
        f"- Provider: `{source_summary.get('provider', '-')}`",
        f"- Model: `{source_summary.get('model', '-')}`",
        f"- Source API: {source_summary.get('source_api', '-')}",
        f"- Query: `{source_summary.get('source_query', '-')}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(rows)
    lines.extend(
        [
            "",
            "## Data Quality",
            "",
            json.dumps(
                {
                    "success": quality.get("success"),
                    "expectation_count": quality.get("expectation_count"),
                    "statistics": quality.get("statistics"),
                    "freshness": freshness,
                },
                indent=2,
                ensure_ascii=True,
            ),
            "",
        ]
    )
    write_text(Path(report_path), "\n".join(lines) + "\n")


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
    """Write a three-state comparison report for baseline/corrupted/repaired."""
    metric_keys = [
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    ]
    lines = [
        "# Corruption Impact Report",
        "",
        "## Performance Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for key, label in metric_keys:
        lines.append(
            f"| {label} | {baseline_metrics.get(key, 0):.3f} | "
            f"{corrupted_metrics.get(key, 0):.3f} | {repaired_metrics.get(key, 0):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Quality Gates",
            "",
            "| State | Quality success | Fresh | Stale ratio |",
            "| :--- | ---: | ---: | ---: |",
            f"| Corrupted | {bool(corrupted_quality.get('success'))} | "
            f"{bool(corrupted_freshness.get('is_fresh'))} | {corrupted_freshness.get('stale_ratio', 0)} |",
            f"| Repaired | {bool(repaired_quality.get('success'))} | "
            f"{bool(repaired_freshness.get('is_fresh'))} | {repaired_freshness.get('stale_ratio', 0)} |",
            "",
            "## Detailed Artifacts",
            "",
            "```text",
            f"Baseline metrics = read_json('data/results/baseline_metrics.json')",
            f"Corrupted metrics = read_json('data/results/corrupted_metrics.json')",
            f"Repaired metrics  = read_json('data/results/repaired_metrics.json')",
            "```",
            "",
        ]
    )
    write_text(Path(report_path), "\n".join(lines) + "\n")
