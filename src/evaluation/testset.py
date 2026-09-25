from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class TestSet:
    samples: list[dict[str, Any]]
    path: Path

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    """Load a persisted test set or build and save a new one."""
    path = Path(output_path)
    if path.exists():
        samples = read_json(path)
        if isinstance(samples, list) and samples:
            return TestSet(samples=samples, path=path)

    samples = _build_samples(df)
    write_json(path, samples)
    return TestSet(samples=samples, path=path)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a ten-question benchmark set across the core question types."""
    samples = _build_samples(df)
    write_json(Path(output_path), samples)
    return samples


def _build_samples(df: pd.DataFrame) -> list[dict[str, Any]]:
    if len(df) < 5:
        raise ValueError("Cleaned dataframe must contain at least 5 papers for the test set.")

    records = [row for _, row in df.iterrows()]
    by_id = {normalize_whitespace(str(row["paper_id"])): row for row in records}

    anchors = {
        "agentic": _pick(records, "Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks", by_id),
        "observability": _pick(records, "Data Observability and Quality Gates for Production RAG Systems", by_id),
        "ghost": _pick(records, "Mitigating Ghost Vectors in Dense Retrieval via Idempotent Indexing", by_id),
        "freshness": _pick(records, "Freshness SLAs for Real-Time LLM Knowledge Augmentation", by_id),
        "corruption": _pick(records, "Synthetic Corruption Testing: Stress-Testing Vector Search Robustness", by_id),
        "evaluation": _pick(records, "Evaluating Retrieval Precision with Token F1 and LLM Judges", by_id),
        "chunking": _pick(records, "Chunking Strategies for Technical Documentation Retrieval", by_id),
        "quality": _pick(records, "Automated Data Quality Profiling with Great Expectations in CI/CD", by_id),
        "semantic": _pick(records, "Semantic Layer Integration for Agentic Text-to-SQL Pipelines", by_id),
        "multiagent": _pick(records, "Multi-Agent Consensus for High-Stakes Fact Verification", by_id),
    }
    if any(row is None for row in anchors.values()):
        raise ValueError("Benchmark anchor papers not found in cleaned dataframe.")

    return [
        _sample(
            "q1",
            "summary",
            "What is the main idea of the paper 'Agentic Retrieval-Augmented Generation for Knowledge-Intensive Tasks'?",
            "Retrieval-Augmented Generation significantly improves large language model accuracy by grounding responses in retrieved passages, using agentic multi-hop reasoning and routing across heterogeneous vector indices.",
            [anchors["agentic"]["paper_id"]],
        ),
        _sample(
            "q2",
            "authors",
            "Who authored the research on data observability and quality gates for production RAG systems?",
            "Anh Tran, Quoc Pham",
            [anchors["observability"]["paper_id"]],
        ),
        _sample(
            "q3",
            "date",
            "When was 'Mitigating Ghost Vectors in Dense Retrieval via Idempotent Indexing' published?",
            "2026-04-18",
            [anchors["ghost"]["paper_id"]],
        ),
        _sample(
            "q4",
            "category",
            "Which field does the work on freshness SLAs for real-time LLM knowledge augmentation belong to?",
            "Data Management, Artificial Intelligence",
            [anchors["freshness"]["paper_id"]],
        ),
        _sample(
            "q5",
            "multi_hop",
            "How do synthetic corruption testing and data quality profiling work together to harden retrieval systems?",
            "Synthetic corruption testing stress-tests vector search robustness, while automated data quality profiling with Great Expectations in CI/CD catches malformed data, together hardening retrieval pipelines.",
            [anchors["corruption"]["paper_id"], _pick(records, "Automated Data Quality Profiling with Great Expectations in CI/CD", by_id)["paper_id"]],
        ),
        _sample_summary("q6", anchors["evaluation"]),
        _sample_authors("q7", anchors["chunking"]),
        _sample_date("q8", anchors["semantic"]),
        _sample_categories("q9", anchors["quality"]),
        _sample_summary("q10", anchors["multiagent"]),
    ]


def _sample_summary(sample_id: str, row: pd.Series) -> dict[str, Any]:
    return _sample(
        sample_id,
        "summary",
        f"What is the main idea of the paper '{row['title']}'?",
        first_sentence(str(row["summary"])),
        [str(row["paper_id"])],
    )


def _sample_authors(sample_id: str, row: pd.Series) -> dict[str, Any]:
    return _sample(
        sample_id,
        "authors",
        f"Who authored the paper '{row['title']}'?",
        str(row["authors_joined"]),
        [str(row["paper_id"])],
    )


def _sample_date(sample_id: str, row: pd.Series) -> dict[str, Any]:
    return _sample(
        sample_id,
        "date",
        f"When was the paper '{row['title']}' published?",
        str(row["published"]),
        [str(row["paper_id"])],
    )


def _sample_categories(sample_id: str, row: pd.Series) -> dict[str, Any]:
    return _sample(
        sample_id,
        "category",
        f"What categories does the paper '{row['title']}' belong to?",
        str(row["categories_joined"]),
        [str(row["paper_id"])],
    )


def _pick(records: list[pd.Series], title: str, by_id: dict[str, pd.Series]) -> pd.Series | None:
    needle = normalize_whitespace(title).lower()
    for row in records:
        if normalize_whitespace(str(row["title"])).lower() == needle:
            return row
    for row in records:
        if normalize_whitespace(str(row["title"])).lower() in needle:
            return row
    return None


def _sample(
    sample_id: str,
    question_type: str,
    question: str,
    ground_truth: str,
    ground_truth_doc_ids: list[str],
) -> dict[str, Any]:
    return {
        "id": sample_id,
        "type": question_type,
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": ground_truth_doc_ids,
    }
