from collections.abc import Sequence

import pandas as pd


def summarize_csv(file_path: str) -> dict[str, object]:
    """Load CSV and return basic stats; expand later with domain insights."""
    df = pd.read_csv(file_path)
    summary: dict[str, object] = {
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "columns": list(df.columns),
    }
    numeric_cols: Sequence[str] = df.select_dtypes(include="number").columns
    summary["numeric_summary"] = df[numeric_cols].describe().to_dict() if numeric_cols else {}
    return summary
