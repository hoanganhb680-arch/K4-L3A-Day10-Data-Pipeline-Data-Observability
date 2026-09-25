from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as expectations
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent

STALE_THRESHOLD_DAYS = 180
STALE_RATIO_LIMIT = 0.25


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the four required GX 1.x expectations plus a freshness SLA gate."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(
        name=f"{report_name}_suite",
        expectations=[
            expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
            expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
            expectations.ExpectColumnValuesToNotBeNull(column="title"),
            expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
            expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
            expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30, max_value=1_000_000),
        ],
    )
    result = batch.validate(suite)

    freshness = _freshness_payload(df)
    quality_payload = {
        "report_name": report_name,
        "success": bool(result.success),
        "expectation_count": len(suite.expectations),
        "validation_results": result.to_json_dict().get("results", []),
        "statistics": dict(getattr(result, "statistics", {}) or {}),
        "freshness": freshness,
    }

    report_path = _quality_report_path(settings, report_name)
    _write_json(report_path, quality_payload)
    return quality_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a freshness SLA summary for the given dataframe."""
    payload = _freshness_payload(df)
    _write_json(Path(report_path), payload)
    return payload


def _freshness_payload(df: pd.DataFrame) -> dict[str, Any]:
    total = int(len(df))
    stale_rows = int((df["age_days"] > STALE_THRESHOLD_DAYS).sum()) if not df.empty else 0
    stale_ratio = stale_rows / total if total else 0.0
    is_fresh = stale_ratio <= STALE_RATIO_LIMIT

    if not df.empty:
        oldest_published = df["published"].min()
        latest_published = df["published"].max()
    else:
        oldest_published = None
        latest_published = None

    return {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": STALE_THRESHOLD_DAYS,
        "allowed_stale_ratio": STALE_RATIO_LIMIT,
        "is_fresh": is_fresh,
    }


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in report_name).strip("_") or "check"
    return settings.paths.quality_dir / f"{safe_name}_quality_report.json"


def _write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
