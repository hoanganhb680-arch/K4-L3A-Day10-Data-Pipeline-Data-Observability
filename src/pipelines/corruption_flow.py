from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json, now_utc
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report


def main() -> None:
    settings = load_settings()
    
    # 1. Load baseline metrics and clean dataset
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    
    # 2. Create corrupted dataframe
    settings.paths.corruption_log.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    
    # 3. Save corrupted artifacts
    settings.paths.corrupted_clean_json.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", force_ascii=False, indent=2)
    
    # 4. Rebuild index and evaluate
    settings.paths.corrupted_embeddings_json.parent.mkdir(parents=True, exist_ok=True)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    
    # 5. Run quality checks/freshness on corrupted data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    
    # 6. Repair again from raw records
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    
    settings.paths.repaired_clean_json.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", force_ascii=False, indent=2)
    
    # 7. Evaluate repaired dataset
    settings.paths.repaired_embeddings_json.parent.mkdir(parents=True, exist_ok=True)
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)
    
    # 8. Create comparison report
    settings.paths.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
