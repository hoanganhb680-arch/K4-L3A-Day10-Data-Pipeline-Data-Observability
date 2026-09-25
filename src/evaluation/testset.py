from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """tao bo evaluation set tu cleaned dataframe."""
    if len(df) == 0:
        write_json(output_path, [])
        return []
        
    test_set = []
    
    num_papers = min(10, len(df))
    sample_df = df.head(num_papers)
    records = sample_df.to_dict("records")
    
    # Distribution of 10 questions across 4 types
    q_types = ["summary", "summary", "summary", "authors", "authors", "authors", "date", "date", "categories", "categories"]
    
    for i in range(10):
        record = records[i % len(records)]
        q_type = q_types[i]
        
        q_id = f"eval_{str(i+1).zfill(3)}"
        title = record["title"]
        paper_id = record["paper_id"]
        
        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(record["summary"]))
        elif q_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = str(record["authors_joined"])
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(record["published"])
        elif q_type == "categories":
            question = f"What are the categories or subjects of the paper '{title}'?"
            ground_truth = str(record["categories_joined"])
            
        test_set.append({
            "id": q_id,
            "question_type": q_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id]
        })
        
    write_json(output_path, test_set)
    return test_set
