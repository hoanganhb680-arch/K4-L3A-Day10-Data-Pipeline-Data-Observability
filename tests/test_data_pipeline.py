from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from core.config import load_settings
from core.utils import read_json, write_json
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks


ROOT = Path(__file__).resolve().parents[1]
RUN_DATE = datetime(2026, 9, 25, tzinfo=UTC)


class DataPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = load_settings(Path(self.temp.name))
        self.payload = read_json(ROOT / "data/raw/crossref_response.json")
        self.records = parse_crossref_payload(self.payload)

    def clean(self):
        return build_clean_dataframe(self.records, RUN_DATE)

    def test_parser_handles_missing_fields_and_markup(self):
        payload = {"message": {"items": [None, {}, {"DOI": "10.TEST/1", "title": [" A <b>title</b> "],
                   "abstract": "<jats:p>A &amp; B</jats:p><p>next</p>", "subject": None,
                   "author": [None, {"given": " A ", "family": " B "}],
                   "published": {"date-parts": [[2026]]}}]}}
        result = parse_crossref_payload(payload)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "A title")
        self.assertEqual(result[0].summary, "A & B next")
        self.assertEqual(result[0].authors, ["A B"])
        self.assertEqual(result[0].published, "2026-01-01")
        for invalid in ({}, {"message": None}, {"message": {"items": None}}):
            self.assertEqual(parse_crossref_payload(invalid), [])

    def test_snapshot_is_preserved_and_roundtrips_without_network(self):
        path = self.settings.paths.raw_api_response
        write_json(path, self.payload)
        before = path.read_bytes()
        with patch("ingestion.crossref.requests.Session") as network:
            fetched = fetch_source_records(self.settings)
            network.assert_not_called()
        self.assertEqual(len(fetched), 24)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(load_raw_records(self.settings.paths.raw_records_json), fetched)

    def test_refresh_failure_falls_back_without_overwriting_snapshot(self):
        path = self.settings.paths.raw_api_response
        write_json(path, self.payload)
        before = path.read_bytes()
        with patch("ingestion.crossref.requests.Session") as network:
            network.return_value.__enter__.return_value.get.side_effect = requests.Timeout()
            self.assertEqual(len(fetch_source_records(replace(self.settings, refresh_source=True))), 24)
        self.assertEqual(path.read_bytes(), before)

    def test_cleaning_is_deterministic_deduplicated_and_recomputes_fields(self):
        records = self.records + [self.records[0], replace(self.records[1], paper_id="bad", published="invalid")]
        first = build_clean_dataframe(records, RUN_DATE)
        second = build_clean_dataframe(list(reversed(records)), RUN_DATE)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), 24)
        self.assertTrue(first.paper_id.is_unique)
        for row in first.itertuples():
            self.assertEqual(row.age_days, (RUN_DATE.date() - datetime.fromisoformat(row.published).date()).days)
            self.assertEqual(row.summary_chars, len(row.summary))
            self.assertIn(f"Summary: {row.summary}", row.text_for_embedding)
        self.assertTrue(build_clean_dataframe([], RUN_DATE).empty)

    def test_benchmark_has_ten_stable_questions_of_four_types(self):
        path = self.settings.paths.eval_testset
        first = build_test_set(self.clean(), path)
        second = build_test_set(self.clean().sample(frac=1, random_state=19), path)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        self.assertEqual(len({item["id"] for item in first}), 10)
        self.assertEqual({item["question_type"] for item in first}, {"summary", "authors", "date", "categories"})
        self.assertTrue(all(item["ground_truth"] and item["ground_truth_doc_ids"] for item in first))

    def test_quality_detects_corruption_and_raw_repair_recovers(self):
        baseline = self.clean()
        baseline_copy = baseline.copy(deep=True)
        corrupted = corrupt_clean_dataframe(baseline, self.settings.paths.corruption_log, run_date=RUN_DATE)
        pd.testing.assert_frame_equal(baseline, baseline_copy)
        again = corrupt_clean_dataframe(baseline, self.settings.paths.corruption_log, run_date=RUN_DATE)
        pd.testing.assert_frame_equal(corrupted, again)
        self.assertEqual(len(read_json(self.settings.paths.corruption_log)["scenarios"]), 6)
        for row in corrupted.itertuples():
            self.assertEqual(row.summary_chars, len(row.summary))
            self.assertEqual(row.age_days, (RUN_DATE.date() - datetime.fromisoformat(row.published).date()).days)
            self.assertIn(f"Title: {row.title}", row.text_for_embedding)
        self.assertTrue(run_data_quality_checks(baseline, self.settings, "baseline")["success"])
        quality = run_data_quality_checks(corrupted, self.settings, "corrupted")
        failed = {(r["expectation"], r["column"]) for r in quality["results"] if not r["success"]}
        self.assertIn(("expect_column_values_to_be_unique", "paper_id"), failed)
        self.assertIn(("expect_column_value_lengths_to_be_between", "summary"), failed)
        self.assertIn(("expect_column_value_lengths_to_be_between", "title"), failed)
        fresh = build_freshness_report(corrupted, self.settings, self.settings.paths.freshness_report)
        self.assertFalse(fresh["is_fresh"])
        self.assertGreater(fresh["stale_ratio"], 0.25)
        repaired = self.clean()
        pd.testing.assert_frame_equal(baseline, repaired)
        self.assertTrue(run_data_quality_checks(repaired, self.settings, "repaired")["success"])

    def test_freshness_boundary_and_empty_input(self):
        path = self.settings.paths.freshness_report
        df = pd.DataFrame({"age_days": [180, 181, 0, 10], "published": ["2026-03-29"] * 4})
        result = build_freshness_report(df, self.settings, path)
        self.assertEqual(result["stale_rows"], 1)
        self.assertTrue(result["is_fresh"])
        df.loc[0, "age_days"] = 181
        self.assertFalse(build_freshness_report(df, self.settings, path)["is_fresh"])
        self.assertFalse(build_freshness_report(df.iloc[:0], self.settings, path)["is_fresh"])


if __name__ == "__main__":
    unittest.main()
