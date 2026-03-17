"""
Data Cleaner

Responsible for transforming raw DataFrames (from :mod:`src.data_loader`)
into clean, analysis-ready ones.

Cleaning pipeline (applied via :func:`clean_dataset`):
    1. normalize_columns      – rename to snake_case, strip whitespace
    2. replace_dash_with_nan  – catch any stray ``-`` / whitespace-only cells
    3. cast_numeric_columns   – coerce to float, turning bad values into NaN
    4. drop_duplicates        – keep first occurrence of each item_name
    5. impute_by_category     – category-median imputation (drinks only)
    6. tag_source             – add ``source`` and ``is_imputed`` columns
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Column name mappings
# ---------------------------------------------------------------------------

_DRINKS_COLUMN_MAP: dict[str, str] = {
    "Calories":   "calories",
    "Fat (g)":    "fat_g",
    "Carb. (g)":  "carb_g",
    "Fiber (g)":  "fiber_g",
    "Protein":    "protein_g",
    "Sodium":     "sodium_mg",
}

_FOOD_COLUMN_MAP: dict[str, str] = {
    "Calories":    "calories",
    "Fat (g)":     "fat_g",
    "Carb. (g)":   "carb_g",
    "Fiber (g)":   "fiber_g",
    "Protein (g)": "protein_g",
}

# ---------------------------------------------------------------------------
# Drink category keyword map
# ---------------------------------------------------------------------------
# Order matters: the first matching keyword wins.

DRINK_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Frappuccino": ["frappuccino"],
    "Macchiato":   ["macchiato"],
    "Latte":       ["latte", "milk"],
    "Mocha":       ["mocha"],
    "Tea":         ["tea", "teavana", "tazo"],
    "Refresher":   ["refresher"],
    "Juice":       ["juice", "evolution fresh"],
    "Espresso":    ["espresso", "americano", "doubleshot"],
    "Coffee":      ["coffee", "cold brew", "roast", "clover", "misto"],
    "Other":       [],
}


def normalize_columns(
    df: pd.DataFrame,
    dataset_type: Literal["drinks", "food"],
) -> pd.DataFrame:
    """
    Strip whitespace from all column names and apply the snake_case map.

    Columns absent from the source file are silently ignored, so this is
    safe to call even on uploaded CSVs that may be missing a column.
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    col_map = _DRINKS_COLUMN_MAP if dataset_type == "drinks" else _FOOD_COLUMN_MAP
    return df.rename(columns=col_map)


def replace_dash_with_nan(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace ``-`` and whitespace-only strings with ``NaN``.

    ``na_values=["-"]`` in :mod:`src.data_loader` already handles most cases;
    this pass catches edge cases such as ``" - "`` (dash with surrounding spaces).
    """
    df = df.copy()
    df = df.replace(r"^\s*-\s*$", np.nan, regex=True)
    df = df.replace(r"^\s*$", np.nan, regex=True)
    return df


def cast_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce every column except meta columns to ``float``.

    ``errors="coerce"`` silently converts any remaining non-numeric value
    (e.g., a stray string) into ``NaN`` rather than raising.
    """
    df = df.copy()
    _META = {"item_name", "source", "category", "is_imputed"}
    for col in df.columns:
        if col not in _META:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows, keeping the first occurrence per ``item_name``."""
    return df.drop_duplicates(subset=["item_name"], keep="first").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Category-based imputation  (drinks only)
# ---------------------------------------------------------------------------

def assign_drink_category(item_name: str) -> str:
    """Map a drink name to its category via keyword matching.

    Iterates :data:`DRINK_CATEGORY_KEYWORDS` in order and returns the first
    category whose keywords appear in the lowercased item name.
    Falls back to ``"Other"`` when no keyword matches.

    Examples
    --------
    >>> assign_drink_category("Iced Skinny Vanilla Latte")
    'Latte'
    >>> assign_drink_category("Starbucks® Bottled Caramel Frappuccino®")
    'Frappuccino'
    >>> assign_drink_category("Ginger Ale")
    'Other'
    """
    name_lower = item_name.lower()
    for category, keywords in DRINK_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category
    return "Other"


def impute_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing numeric values using per-category medians.

    Strategy
    --------
    1. Assign each row a drink category via :func:`assign_drink_category`.
    2. Compute per-column medians **within each category** from complete rows only.
    3. For each NaN cell, substitute the category median.
    4. If the category median is itself NaN (no complete rows for that column
       in that category), fall back to the **global** column median.
    5. Mark any row with at least one imputed value as ``is_imputed=True``.

    Returns
    -------
    pd.DataFrame
        DataFrame with NaN cells filled and two new columns:
        ``category`` (str) and ``is_imputed`` (bool).
    """
    df = df.copy()
    numeric_cols = _get_numeric_cols(df)

    df["category"] = df["item_name"].apply(assign_drink_category)
    df["is_imputed"] = False

    # Global medians — fallback
    global_medians: dict[str, float] = {
        col: float(df[col].median(skipna=True)) for col in numeric_cols
    }

    # Per-category medians (computed from complete rows only)
    category_medians: dict[str, dict[str, float]] = {}
    for cat in df["category"].unique():
        cat_rows = df[df["category"] == cat]
        category_medians[cat] = {
            col: float(cat_rows[col].median(skipna=True)) for col in numeric_cols
        }

    for idx, row in df.iterrows():
        missing = [c for c in numeric_cols if pd.isna(row[c])]
        if not missing:
            continue

        cat = row["category"]
        df.at[idx, "is_imputed"] = True

        for col in missing:
            cat_median = category_medians[cat].get(col, np.nan)
            df.at[idx, col] = (
                cat_median
                if not np.isnan(cat_median)
                else global_medians.get(col, 0.0)
            )

    return df


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def clean_dataset(
    df: pd.DataFrame,
    dataset_type: Literal["drinks", "food"],
) -> pd.DataFrame:
    """
    Run the full cleaning pipeline and return an analysis-ready DataFrame.

    Parameters
    ----------
    df:
        Raw DataFrame from :func:`~src.data_loader.load_csv`.
    dataset_type:
        ``"drinks"`` or ``"food"``.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with columns normalised to snake_case, numeric
        values cast to float, duplicates removed, missing values imputed
        (drinks only), and ``source`` / ``is_imputed`` meta columns added.
    """
    df = normalize_columns(df, dataset_type)
    df = replace_dash_with_nan(df)
    df = cast_numeric_columns(df)
    df = drop_duplicates(df)

    if dataset_type == "drinks":
        df = impute_by_category(df)
    else:
        df["category"] = "Food"
        df["is_imputed"] = False

    df["source"] = dataset_type
    return df


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_numeric_cols(df: pd.DataFrame) -> list[str]:
    """Numeric columns, excluding internal meta columns."""
    _EXCLUDE = {"is_imputed"}
    return [c for c in df.select_dtypes(include="number").columns if c not in _EXCLUDE]
