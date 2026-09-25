from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc
from ingestion.crossref import fetch_source_records, load_raw_records, save_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report


def main() -> None:
    settings = load_settings()
    
    if settings.paths.raw_records_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
    else:
        raw_records = fetch_source_records(settings)
        save_raw_records(raw_records, settings.paths.raw_records_json)
        
    df = build_clean_dataframe(raw_records, now_utc())
    
    # Ensure parents exist
    settings.paths.clean_json.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(settings.paths.clean_json, orient="records", force_ascii=False, indent=2)
    
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    
    settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
    build_test_set(df, settings.paths.eval_testset)
    
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.eval_metrics,
        answers_output_path=settings.paths.eval_answers,
    )
    
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    
    source_summary = {
        "raw_count": len(raw_records),
        "clean_count": len(df),
    }
    
    settings.paths.phase1_report.parent.mkdir(parents=True, exist_ok=True)
    generate_phase1_report(
        report_path=settings.paths.phase1_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
