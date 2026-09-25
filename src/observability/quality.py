from __future__ import annotations

from typing import Any
from pathlib import Path

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate the dataframe with GX Core 1.x and save auditable results."""
    context = gx.get_context(mode="ephemeral")
    context.variables.progress_bars = {"globally": False}
    source = context.data_sources.add_pandas(name="papers_source")
    asset = source.add_dataframe_asset(name="papers_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    expectations = [gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)]
    for column in ("paper_id", "title", "text_for_embedding", "summary", "age_days"):
        expectations.append(gx.expectations.ExpectColumnValuesToNotBeNull(column=column))
    expectations.extend([
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="paper_id", min_value=1),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="text_for_embedding", min_value=1),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
        gx.expectations.ExpectColumnValuesToBeBetween(column="age_days", min_value=0),
    ])
    results = []
    for expectation in expectations:
        validation = batch.validate(expectation).to_json_dict()
        results.append({"expectation": expectation.expectation_type,
                        "column": getattr(expectation, "column", None),
                        "success": bool(validation["success"]), "result": validation["result"]})
    failed = sum(not result["success"] for result in results)
    report = {"success": failed == 0, "row_count": len(df), "gx_version": gx.__version__,
              "evaluated_expectations": len(results), "failed_expectations": failed, "results": results}
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Alert above 25% stale rows, treating unknown/future ages as invalid."""
    dates = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    invalid_rows = int((dates.isna() | ages.isna() | ages.lt(0)).sum())
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    total = len(df)
    ratio = stale_rows / total if total else 0.0
    report = {
        "latest_published": dates.max().date().isoformat() if dates.notna().any() else None,
        "oldest_published": dates.min().date().isoformat() if dates.notna().any() else None,
        "stale_rows": stale_rows, "total_rows": total, "stale_ratio": ratio,
        "invalid_rows": invalid_rows, "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25, "is_fresh": bool(total and not invalid_rows and ratio <= 0.25),
    }
    write_json(Path(report_path), report)
    return report
