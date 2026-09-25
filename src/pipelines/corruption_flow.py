from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings, normalized_provider
from core.utils import file_sha256, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

def main() -> None:
    """Corrupt a baseline copy, then rebuild repaired data from trusted raw records."""
    settings = load_settings()
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    run_date = datetime.fromisoformat(baseline_metrics["run_date"]).replace(tzinfo=UTC)
    for key, path in (("test_set_sha256", settings.paths.eval_testset),
                      ("raw_records_sha256", settings.paths.raw_records_json),
                      ("clean_data_sha256", settings.paths.clean_json)):
        if file_sha256(path) != baseline_metrics[key]:
            raise RuntimeError(f"Baseline lineage changed ({key}); re-run phase1 before comparing states.")
    for key, value in (("llm_provider", normalized_provider(settings)), ("llm_model", settings.model_name),
                       ("embedding_model", settings.embedding_model), ("top_k", settings.top_k)):
        if baseline_metrics[key] != value:
            raise RuntimeError(f"Evaluation configuration changed ({key}); re-run phase1 first.")
    print(f"Starting corruption/repair against baseline date {run_date.date()}", flush=True)
    baseline_df = pd.DataFrame(read_json(settings.paths.clean_json))
    if baseline_df.empty:
        raise RuntimeError("Baseline clean dataset is missing or empty; run phase1 first.")
    corrupted = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log,
                                        run_date=run_date,
                                        freshness_threshold_days=settings.freshness_threshold_days)
    write_csv(corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")
    print(f"Corrupted quality={corrupted_quality['success']}; indexing only in isolated lab collection for impact measurement.", flush=True)
    corrupted_index = LocalEmbeddingIndex.build(corrupted, settings, settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(settings, corrupted_index, settings.paths.eval_testset,
                                         settings.paths.corrupted_metrics, settings.paths.corrupted_answers)

    repaired_df = build_clean_dataframe(load_raw_records(settings.paths.raw_records_json), run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json")
    if not repaired_quality["success"]:
        raise RuntimeError("Repaired quality gate failed; refusing to index invalid data.")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(settings, repaired_index, settings.paths.eval_testset,
                                        settings.paths.repaired_metrics, settings.paths.repaired_answers)
    generate_corruption_report(settings.paths.comparison_report, baseline_metrics,
                               corrupted_bundle.summary, repaired_bundle.summary,
                               corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness)
    print("Corruption flow complete:")
    print(f"  quality: baseline={baseline_metrics.get('quality_status', 'UNKNOWN')} corrupted={corrupted_quality['success']} repaired={repaired_quality['success']}")
    print(f"  freshness: baseline={baseline_metrics.get('freshness_status', 'UNKNOWN')} corrupted={corrupted_freshness['is_fresh']} repaired={repaired_freshness['is_fresh']}")
    for name, bundle in (("baseline", baseline_metrics), ("corrupted", corrupted_bundle.summary), ("repaired", repaired_bundle.summary)):
        print(f"  {name}: hit_rate={bundle.get('retrieval_hit_rate')} token_f1={bundle.get('mean_token_f1')}")
