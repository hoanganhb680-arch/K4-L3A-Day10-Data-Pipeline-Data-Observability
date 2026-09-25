from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build ten reproducible questions spread across the publication range.

    The pipeline owns the refresh decision; this function explicitly writes a new set.
    """
    papers = df.sort_values(["published", "paper_id"], ascending=[False, True]).drop_duplicates("paper_id")
    required = ["title", "summary", "authors_joined", "published", "categories_joined"]
    papers = papers.loc[papers[required].fillna("").ne("").all(axis=1)].reset_index(drop=True)
    if len(papers) < 5:
        raise ValueError("At least five papers with complete benchmark fields are required.")
    types = ["summary", "authors", "date", "categories", "summary", "authors", "date", "categories", "summary", "authors"]
    items = []
    for index, question_type in enumerate(types):
        row = papers.iloc[round(index * (len(papers) - 1) / 9)]
        questions = {
            "summary": (f"What is the summary of the paper '{row.title}'?", first_sentence(row.summary)),
            "authors": (f"Who authored the paper '{row.title}'?", row.authors_joined),
            "date": (f"When was the paper '{row.title}' published?", row.published),
            "categories": (f"What categories describe the paper '{row.title}'?", row.categories_joined),
        }
        question, ground_truth = questions[question_type]
        items.append({"id": f"eval_{index + 1:03d}", "question_type": question_type,
                      "question": question, "ground_truth": ground_truth,
                      "ground_truth_doc_ids": [row.paper_id]})
    write_json(output_path, items)
    return items
