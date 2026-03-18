"""Shared inventory table styling."""
from __future__ import annotations

import pandas as pd


def style_inventory(
    df: pd.DataFrame,
    grade_col: str | None = None,
    grade_styles: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Return a styles DataFrame for use with df.style.apply(..., axis=None).

    - Numeric columns: values > median+std → red, < median-std → green.
    - Optional grade_col: applies per-value background colour from grade_styles.
    """
    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    for col in df.select_dtypes(include="number").columns:
        med, std = df[col].median(), df[col].std()
        for idx in df.index:
            v = df.at[idx, col]
            if pd.notna(v):
                if v > med + std:
                    styles.at[idx, col] = "color: #dc2626; font-weight: 600"
                elif v < med - std:
                    styles.at[idx, col] = "color: #16a34a; font-weight: 600"

    if grade_col and grade_styles and grade_col in df.columns:
        for idx in df.index:
            styles.at[idx, grade_col] = grade_styles.get(df.at[idx, grade_col], "")

    return styles
