from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import random

import pandas as pd

from core.utils import ensure_parent, write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six corruption scenarios and record a reproducible audit log."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    corrupted = df.copy()
    log: dict[str, object] = {
        "input_rows": int(len(df)),
        "scenarios": [],
        "indices": {},
    }

    # 1. Stale date: shift several newest records back 365 days.
    stale_count = max(1, int(round(len(corrupted) * 0.2)))
    stale_idx = corrupted.sort_values("published", ascending=False).head(stale_count).index.tolist()
    corrupted.loc[stale_idx, "published"] = (
        pd.to_datetime(corrupted.loc[stale_idx, "published"], errors="coerce")
        - pd.Timedelta(days=365)
    ).dt.strftime("%Y-%m-%d")
    new_dates = pd.to_datetime(corrupted.loc[stale_idx, "published"], errors="coerce")
    corrupted.loc[stale_idx, "age_days"] = (
        (pd.Timestamp(datetime.now(timezone.utc).date()) - new_dates).dt.days
    )
    _rebuild_embedding(corrupted)
    _append_log(log, "stale_date", "Shifted published dates back 365 days for selected newest rows.", stale_idx)

    # 2. Blank summary in a few rows.
    blank_count = max(1, int(round(len(corrupted) * 0.15)))
    blank_idx = corrupted.sample(blank_count, random_state=21).index.tolist()
    corrupted.loc[blank_idx, "summary"] = ""
    corrupted.loc[blank_idx, "summary_chars"] = 0
    _rebuild_embedding(corrupted)
    _append_log(log, "blank_summary", "Cleared summary and rebuilt embedding text.", blank_idx)

    # 3. Inject noise into summary text.
    noise_count = max(1, int(round(len(corrupted) * 0.2)))
    noise_idx = corrupted.sample(noise_count, random_state=33).index.tolist()
    noise = "!!![]ZLIB_CORRUPTED<<>>"
    corrupted.loc[noise_idx, "summary"] = corrupted.loc[noise_idx, "summary"].astype(str) + " " + noise
    corrupted.loc[noise_idx, "summary_chars"] = corrupted.loc[noise_idx, "summary"].astype(str).str.len()
    _rebuild_embedding(corrupted)
    _append_log(log, "inject_noise", "Injected a garbage token into summary text.", noise_idx)

    # 4. Truncate title below 8 characters.
    title_count = max(1, int(round(len(corrupted) * 0.15)))
    title_idx = corrupted.sample(title_count, random_state=7).index.tolist()
    corrupted.loc[title_idx, "title"] = corrupted.loc[title_idx, "title"].astype(str).str[:5] + "..."
    _rebuild_embedding(corrupted)
    _append_log(log, "truncate_title", "Truncated titles to below the required length.", title_idx)

    # 5. Duplicate rows.
    dup_count = max(1, int(round(len(corrupted) * 0.2)))
    dup_idx = corrupted[~corrupted.index.isin(corrupted.index[:dup_count])].sample(
        min(dup_count, len(corrupted)), random_state=11
    ).index.tolist()
    corrupted = pd.concat([corrupted, corrupted.loc[dup_idx]], ignore_index=True)
    _append_log(log, "duplicate_rows", "Duplicated selected rows.", dup_idx)

    # 6. Drop latest records (20% by recency).
    drop_count = max(1, int(round(len(corrupted) * 0.2)))
    dropped_idx = corrupted.sort_values("published", ascending=False).head(drop_count).index.tolist()
    corrupted = corrupted.drop(index=dropped_idx).reset_index(drop=True)
    _append_log(log, "drop_latest", "Dropped the newest records to simulate stale serving data.", dropped_idx)

    log["output_rows"] = int(len(corrupted))
    _write_log(output_log_path, log)
    return corrupted


def _rebuild_embedding(df: pd.DataFrame) -> None:
    df["text_for_embedding"] = df.apply(_embedding_text, axis=1)


def _embedding_text(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row.get('title', '')}",
            f"Authors: {row.get('authors_joined', '')}",
            f"Published: {row.get('published', '')}",
            f"Categories: {row.get('categories_joined', '')}",
            f"Summary: {row.get('summary', '')}",
        ]
    )


def _append_log(log: dict[str, object], name: str, description: str, indices: list[int]) -> None:
    log["scenarios"].append({"name": name, "description": description, "affected_rows": int(len(indices))})
    log["indices"][name] = [int(i) for i in indices]


def _write_log(path, payload: dict[str, object]) -> None:
    write_json(Path(path), payload)
