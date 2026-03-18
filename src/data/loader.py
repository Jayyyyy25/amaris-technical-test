"""
Data Loader

Responsible for reading CSV files off disk and returning raw DataFrames.
No business logic here, only I/O, encoding detection, and basic structural fixes.
"""

import io
from pathlib import Path
from typing import Literal

import chardet
import pandas as pd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

DatasetType = Literal["drinks", "food"]


def load_csv(filepath: str | Path, dataset_type: DatasetType) -> pd.DataFrame:
    """Load a Starbucks nutrition CSV and return a raw DataFrame.

    Handles two known quirks in the source files:
    - *Drinks*: standard UTF-8/Latin-1 encoding; missing values stored as ``-``.
    - *Food*: UTF-16 LE with BOM; all rows have numeric data.

    The first (unnamed) column is renamed to ``item_name``.
    No further cleaning is performed here.

    Parameters
    ----------
    filepath:
        Path to the CSV file.
    dataset_type:
        ``"drinks"`` or ``"food"``.  Controls the encoding strategy.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with ``item_name`` as the first column.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset not found: {filepath}")

    if dataset_type == "food":
        df = _load_food_csv(filepath)
    else:
        df = _load_drinks_csv(filepath)

    df = _rename_item_column(df)
    return df


def load_both_datasets(
    drinks_path: str | Path,
    food_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience wrapper — load both CSVs in one call.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        ``(drinks_raw, food_raw)`` — both are raw, uncleaned DataFrames.
    """
    drinks_raw = load_csv(drinks_path, dataset_type="drinks")
    food_raw = load_csv(food_path, dataset_type="food")
    return drinks_raw, food_raw


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_encoding(filepath: Path, sample_bytes: int = 10_000) -> str:
    """Detect the character encoding of a file using chardet.

    Falls back to ``"utf-8"`` if detection is inconclusive.
    """
    with open(filepath, "rb") as fh:
        raw = fh.read(sample_bytes)
    result = chardet.detect(raw)
    encoding = result.get("encoding") or "utf-8"
    return encoding


def _load_drinks_csv(filepath: Path) -> pd.DataFrame:
    """Load the drinks CSV.

    Uses chardet for encoding detection and marks ``-`` as NaN at parse time
    so downstream numeric casting has less work to do.
    """
    encoding = _detect_encoding(filepath)
    df = pd.read_csv(
        filepath,
        encoding=encoding,
        na_values=["-"],       # treat dash as missing from the start
        keep_default_na=True,
    )
    return df


def _load_food_csv(filepath: Path) -> pd.DataFrame:
    """Load the food CSV.

    The file is encoded as UTF-16 LE with a BOM.  ``pandas`` handles the BOM
    automatically when ``encoding="utf-16"`` is specified — the byte-pair
    spacing that appears when the file is read as ASCII disappears.

    If chardet detects a UTF-16 variant we use that; otherwise we fall back
    to the known encoding.
    """
    detected = _detect_encoding(filepath)
    encoding = detected if "utf-16" in detected.lower() else "utf-16"

    df = pd.read_csv(filepath, encoding=encoding)

    # Strip any residual BOM character from the first column name.
    # pandas usually removes it, but this is a safety net.
    first_col = df.columns[0].lstrip("\ufeff").strip()
    df.columns = [first_col] + list(df.columns[1:])

    return df


def _rename_item_column(df: pd.DataFrame) -> pd.DataFrame:
    """Rename the unnamed first column (item names) to ``item_name``."""
    first = df.columns[0]

    if first == "" or first.startswith("Unnamed"):
        df = df.rename(columns={first: "item_name"})
    elif first != "item_name":
        df = df.rename(columns={first: "item_name"})
    return df
