from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the clean-data Phase 1 pipeline end to end and emit all artifacts."""
    settings = load_settings()

    fetch_source_records(settings)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    test_set = load_or_create_test_set(clean_df, settings.paths.eval_testset)
    print(f"[phase1] clean rows: {len(clean_df)}")
    print(f"[phase1] test samples: {len(test_set.samples)}")
    print(f"[phase1] chroma collection: {index.collection_name}")

    bundle = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    source_summary = {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "records": len(clean_df),
        "test_samples": len(test_set.samples),
        "collection_name": index.collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        bundle.summary,
        quality,
        freshness,
    )

    print(f"[phase1] retrieval_hit_rate: {bundle.summary['retrieval_hit_rate']:.3f}")
    print(f"[phase1] mean_token_f1: {bundle.summary['mean_token_f1']:.3f}")
    print(f"[phase1] quality success: {quality['success']}")
    print(f"[phase1] report: {settings.paths.baseline_report}")
