from __future__ import annotations

import pandas as pd

from core.utils import write_json, normalize_whitespace


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """simulate nhieu dang data corruption."""
    if df.empty:
        write_json(output_log_path, ["Empty dataframe, no corruption applied."])
        return df

    cdf = df.copy()
    logs = []

    # 1. Drop a few rows (e.g. 10%)
    drop_count = max(1, int(len(cdf) * 0.1))
    dropped_ids = cdf.head(drop_count)["paper_id"].tolist()
    cdf = cdf.iloc[drop_count:].copy()
    logs.append(f"Dropped {drop_count} latest records: {dropped_ids}")
    
    if cdf.empty:
        write_json(output_log_path, logs)
        return cdf

    # 2. Blank summary in first row
    cdf.iloc[0, cdf.columns.get_loc('summary')] = ""
    logs.append(f"Blanked summary for paper_id: {cdf.iloc[0]['paper_id']}")
    
    # 3. Inject noise into text
    cdf.iloc[0, cdf.columns.get_loc('authors_joined')] = "NULL_AUTHOR_999"
    
    # 4. Truncate title for the second row
    if len(cdf) > 1:
        old_title = cdf.iloc[1]['title']
        cdf.iloc[1, cdf.columns.get_loc('title')] = old_title[:3]
        logs.append(f"Truncated title for paper_id: {cdf.iloc[1]['paper_id']}")

    # 5. Make published date older to fail freshness
    cdf['age_days'] = cdf['age_days'] + 200
    logs.append("Increased age_days by 200 for all records to simulate staleness.")

    # 6. Add duplicate rows
    duplicate_row = cdf.iloc[0:1].copy()
    cdf = pd.concat([cdf, duplicate_row], ignore_index=True)
    logs.append(f"Added duplicate row for paper_id: {duplicate_row.iloc[0]['paper_id']}")

    # 7. Rebuild text_for_embedding
    cdf["text_for_embedding"] = cdf.apply(
        lambda row: (
            f"Title: {normalize_whitespace(str(row['title']))}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {normalize_whitespace(str(row['summary']))}"
        ),
        axis=1
    )

    # 8. Write logs
    write_json(output_log_path, logs)

    return cdf
