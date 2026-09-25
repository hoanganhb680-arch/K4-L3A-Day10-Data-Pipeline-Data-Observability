from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord, as_list, clean_text


def rebuild_derived_columns(df: pd.DataFrame, run_date: datetime) -> pd.DataFrame:
    """Recompute derived fields without filtering or deduplicating corrupt rows."""
    result = df.copy(deep=True)
    published = pd.to_datetime(result["published"], errors="coerce", utc=True, format="mixed")
    reference = pd.Timestamp(run_date)
    reference = reference.tz_localize("UTC") if reference.tzinfo is None else reference.tz_convert("UTC")
    result["age_days"] = (reference.normalize() - published.dt.normalize()).dt.days.astype("Int64")
    result["summary_chars"] = result["summary"].fillna("").str.len()
    result["text_for_embedding"] = [
        f"Title: {row.title}\nAuthors: {row.authors_joined}\nPublished: {row.published}\n"
        f"Categories: {row.categories_joined}\nSummary: {row.summary}"
        for row in result.itertuples()
    ]
    return result


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize text/dates and retain one deterministic version of each DOI."""
    df = pd.DataFrame([asdict(record) for record in records], columns=[field.name for field in fields(PaperRecord)])
    for column in df.columns.difference(["authors", "categories"]):
        df[column] = df[column].map(clean_text)
    df["paper_id"] = df["paper_id"].str.lower()
    for column in ("authors", "categories"):
        df[column] = df[column].map(lambda values: list(dict.fromkeys(
            text for value in as_list(values) if (text := clean_text(value)))))
    for column in ("published", "updated"):
        parsed = pd.to_datetime(df[column], errors="coerce", utc=True, format="mixed")
        df[column] = parsed.dt.strftime("%Y-%m-%d").fillna("")
    # A missing identifier, title, or publication date cannot support this lab's contract.
    df = df.loc[df["paper_id"].ne("") & df["title"].ne("") & df["published"].ne("")].copy()
    df["updated"] = df["updated"].where(df["updated"].ne(""), df["published"])
    df["authors_joined"] = df["authors"].map(", ".join)
    df["categories_joined"] = df["categories"].map(", ".join)
    df["primary_category"] = df["categories"].map(lambda values: values[0] if values else "")
    df = rebuild_derived_columns(df, run_date)
    # Prefer latest metadata, then the most complete abstract; break ties by content.
    df = df.sort_values(["paper_id", "updated", "summary_chars", "text_for_embedding"],
                        ascending=[True, False, False, True], kind="stable")
    return df.drop_duplicates("paper_id").sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable").reset_index(drop=True)
