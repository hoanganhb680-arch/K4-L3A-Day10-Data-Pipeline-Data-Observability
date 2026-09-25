from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord

_EMBEDDING_FIELDS = ("paper_id", "title", "summary", "authors", "categories", "published", "updated", "abs_url", "pdf_url", "primary_category")


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Convert raw records into a clean, deduplicated embedding-ready dataframe."""
    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title or not summary:
            continue

        authors = [normalize_whitespace(author) for author in record.authors]
        authors = list(dict.fromkeys(author for author in authors if author))
        categories = [normalize_whitespace(category) for category in record.categories]
        categories = list(dict.fromkeys(category for category in categories if category))

        published = normalize_whitespace(record.published)
        updated = normalize_whitespace(record.updated) or published
        published_dt = _parse_datetime(published)
        updated_dt = _parse_datetime(updated)
        if published_dt is None:
            continue

        age_days = (run_date.date() - published_dt.date()).days
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        primary_category = normalize_whitespace(record.primary_category) or (categories[0] if categories else "")
        summary_chars = len(summary)
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined or 'Unknown'}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined or 'Unknown'}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
            }
        )

    if not rows:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories", "primary_category",
            "published", "updated", "age_days",
            "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
            "abs_url", "pdf_url", "comment",
        ])

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"], keep="first").copy()

    expected_columns = [
        "paper_id", "title", "summary", "published", "updated", "age_days",
        "authors", "categories", "primary_category",
        "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
        "abs_url", "pdf_url", "comment",
    ]
    df = df[expected_columns]
    return df.sort_values(["published", "paper_id"], kind="stable").reset_index(drop=True)


def _parse_datetime(value: str) -> datetime | None:
    value = normalize_whitespace(value)
    if not value:
        return None
    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except Exception:
        parsed = pd.NaT
    if pd.isna(parsed):
        return None
    if getattr(parsed, "tzinfo", None) is not None:
        parsed = parsed.tz_localize(None)
    return parsed.to_pydatetime()
