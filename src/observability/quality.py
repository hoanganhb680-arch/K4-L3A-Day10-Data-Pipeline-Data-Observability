from __future__ import annotations

from typing import Any

import pandas as pd
import great_expectations as gx
import great_expectations.expectations as gxe

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """tao bo data quality checks."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    
    suite_name = f"papers_suite_{report_name}"
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))
    
    validation_result = batch.validate(suite)
    result_dict = validation_result.to_json_dict()
    
    # Save the quality report
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
        
    write_json(report_path, result_dict)
    return result_dict


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """tong hop freshness report."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False
        }
        write_json(report_path, report)
        return report

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    
    stale_mask = df["age_days"] > settings.freshness_threshold_days
    stale_rows = int(stale_mask.sum())
    
    # is_fresh = False if > 25% of rows are stale
    is_fresh = True
    if (stale_rows / total_rows) > 0.25:
        is_fresh = False
        
    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh
    }
    
    write_json(report_path, report)
    return report
