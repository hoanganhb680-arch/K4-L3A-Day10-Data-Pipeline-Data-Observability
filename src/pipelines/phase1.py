from __future__ import annotations

from datetime import UTC, datetime
import os

from core.config import load_settings
from core.utils import file_sha256, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

def main() -> None:
    """Run the offline-first baseline pipeline from raw ingestion to report."""
    settings = load_settings()
    run_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"Starting baseline: provider={settings.llm_provider}, run_date={run_date.date()}", flush=True)
    records = fetch_source_records(settings)
    df = build_clean_dataframe(records, run_date)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline quality gate failed; refusing to index invalid data.")

    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
    if (len(test_set) != 10
            or {item.get("question_type") for item in test_set} != {"summary", "authors", "date", "categories"}
            or len({item.get("id") for item in test_set}) != 10
            or any(not item.get("ground_truth") or not item.get("question")
                   or not item.get("ground_truth_doc_ids") for item in test_set)):
        raise ValueError("Existing benchmark is invalid. Set REFRESH_TEST_SET=true explicitly to rebuild it.")
    if any(doc_id not in set(df.paper_id) for item in test_set for doc_id in item["ground_truth_doc_ids"]):
        raise ValueError("Fixed benchmark refers to papers absent from the baseline. Refresh the source or explicitly refresh the benchmark.")
    bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset,
                               settings.paths.baseline_metrics, settings.paths.baseline_answers)
    bundle.summary.update({"quality_status": "PASS" if quality["success"] else "FAIL",
                           "freshness_status": "PASS" if freshness["is_fresh"] else "FAIL",
                           "run_date": run_date.date().isoformat(),
                           "raw_records_sha256": file_sha256(settings.paths.raw_records_json),
                           "clean_data_sha256": file_sha256(settings.paths.clean_json)})
    write_json(settings.paths.baseline_metrics, bundle.summary)

    source_summary = {
        "dataset_size": len(df), "source": settings.source_api + " format; preserved local response",
        "run_date": run_date.date().isoformat(), "refresh_source": settings.refresh_source,
        "embedding_model": settings.embedding_model, "collection": index.collection_name,
        "test_set_size": len(test_set), "llm_provider": settings.llm_provider,
        "artifact_paths": [str(path.relative_to(settings.paths.project_dir)) for path in (
            settings.paths.raw_api_response, settings.paths.raw_records_json, settings.paths.clean_csv,
            settings.paths.clean_json, settings.paths.embeddings_json, settings.paths.eval_testset,
            settings.paths.baseline_metrics, settings.paths.baseline_answers,
            settings.paths.baseline_quality_report, settings.paths.freshness_report,
            settings.paths.baseline_report)],
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, bundle.summary, quality, freshness)
    if os.getenv("RUN_AGENT_DEMO", "").lower() in {"1", "true", "yes"}:
        from retrieval.agent import build_agent, run_agent_question
        question = test_set[0]["question"]
        write_json(settings.paths.demo_answers, [{"question": question,
                   "answer": run_agent_question(build_agent(settings, index), question)}])
    print(f"Baseline complete: {len(df)} records, quality={quality['success']}, freshness={freshness['is_fresh']}")
