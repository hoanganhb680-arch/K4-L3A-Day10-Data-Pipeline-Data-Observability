from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import rebuild_derived_columns


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path, *, run_date: datetime | None = None,
                            freshness_threshold_days: int = 180) -> pd.DataFrame:
    """Apply six deterministic faults, retaining bad rows for actual validation."""
    if len(df) < 5:
        raise ValueError("The corruption exercise requires at least five baseline rows.")
    run_date = run_date or now_utc()
    corrupted = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True).copy(deep=True)
    drop_count = min(ceil(len(corrupted) * 0.2), len(corrupted) - 1)
    dropped = corrupted.iloc[:drop_count]
    scenarios = [{"type": "drop_latest_records", "affected_records": drop_count,
                  "paper_ids": dropped.paper_id.tolist(), "parameters": {"fraction": 0.2},
                  "rows_before": len(corrupted), "rows_after": len(corrupted) - drop_count}]
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)
    count = max(1, len(corrupted) // 6)

    def change(kind, indices, column, transform, parameters):
        changes = []
        for index in indices:
            before = corrupted.at[index, column]
            after = transform(before)
            corrupted.at[index, column] = after
            changes.append({"index": int(index), "paper_id": corrupted.at[index, "paper_id"],
                            "before": str(before)[:160], "after": str(after)[:160]})
        scenarios.append({"type": kind, "affected_records": len(changes),
                          "paper_ids": [item["paper_id"] for item in changes],
                          "parameters": parameters, "changes": changes})

    change("blank_summary", range(count), "summary", lambda value: "", {"count": count})
    noise = "ZXQ_NOISE 0000 @@ BROKEN CONTENT. "
    change("inject_noise", range(count, count * 2), "summary", lambda value: noise * 5 + value,
           {"prefix": noise, "repetitions": 5})
    change("truncate_title", range(count * 2, count * 3), "title", lambda value: value[:7], {"max_chars": 7})
    shift = max(365, freshness_threshold_days + 1)
    stale_count = ceil(len(corrupted) * 0.4)
    change("stale_date", range(stale_count), "published",
           lambda value: (datetime.fromisoformat(value) - timedelta(days=shift)).date().isoformat(),
           {"shift_days": shift, "fraction": 0.4})
    duplicates = corrupted.tail(min(2, len(corrupted))).copy()
    scenarios.append({"type": "duplicate_rows", "affected_records": len(duplicates),
                      "paper_ids": duplicates.paper_id.tolist(), "parameters": {"copies_per_row": 1},
                      "rows_before": len(corrupted), "rows_after": len(corrupted) + len(duplicates)})
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    corrupted = rebuild_derived_columns(corrupted, run_date)
    write_json(Path(output_log_path), {"run_date": run_date.date().isoformat(),
               "selection": "published descending, paper_id ascending; fixed positional slices",
               "input_rows": len(df), "output_rows": len(corrupted), "scenarios": scenarios})
    return corrupted
