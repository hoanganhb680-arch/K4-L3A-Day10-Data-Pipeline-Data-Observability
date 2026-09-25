from __future__ import annotations

import dataclasses
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """clean raw records thanh dataframe san sang de embed."""
    if not records:
        return pd.DataFrame()

    # Convert records to dataframe
    df = pd.DataFrame([dataclasses.asdict(r) for r in records])

    # Drop duplicates
    df = df.drop_duplicates(subset=["paper_id"], keep="first").copy()

    # Filter invalid rows
    df = df.dropna(subset=["paper_id", "title", "summary"])
    df = df[df["paper_id"] != ""]
    df = df[df["title"] != ""]
    df = df[df["summary"] != ""]

    if df.empty:
        return df

    # Calculate age_days
    published_dt = pd.to_datetime(df["published"], errors="coerce", utc=True)
    if run_date.tzinfo is None:
        import datetime as dt
        run_date = run_date.replace(tzinfo=dt.timezone.utc)
        
    df["age_days"] = (run_date - published_dt).dt.days
    df["age_days"] = df["age_days"].fillna(0).astype(int)

    # Helper columns
    df["authors_joined"] = df["authors"].apply(lambda x: compact_join(x) if isinstance(x, list) else str(x))
    df["categories_joined"] = df["categories"].apply(lambda x: compact_join(x) if isinstance(x, list) else str(x))
    df["summary_chars"] = df["summary"].apply(lambda x: len(str(x)))

    # Build text_for_embedding
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {normalize_whitespace(str(row['title']))}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {normalize_whitespace(str(row['summary']))}"
        ),
        axis=1
    )

    # Sort by published date descending
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df
