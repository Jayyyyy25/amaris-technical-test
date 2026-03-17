"""
Data Processor

Computes statistics, comparisons, rankings, filtered views, and Plotly
visualisations from the clean DataFrames produced by :mod:`src.data_cleaner`.

This module contains no I/O and no cleaning logic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Constants used by charts and the Streamlit UI
# ---------------------------------------------------------------------------

# Human-readable axis / header labels, keyed by snake_case column name
COLUMN_LABELS: dict[str, str] = {
    "calories":   "Calories (kcal)",
    "fat_g":      "Fat (g)",
    "carb_g":     "Carbs (g)",
    "fiber_g":    "Fiber (g)",
    "protein_g":  "Protein (g)",
    "sodium_mg":  "Sodium (mg)",
}

# Columns present in both datasets (used for cross-dataset comparison)
SHARED_NUMERIC_COLS: list[str] = [
    "calories", "fat_g", "carb_g", "fiber_g", "protein_g",
]


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def compute_descriptive_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """
    Return descriptive statistics for every numeric column in *df*.

    Returns
    -------
    dict
        ``{column_name: {"count", "total", "mean", "median", "std", "min", "max"}}``
    """
    numeric_cols = get_available_numeric_columns(df)
    stats: dict[str, dict[str, float]] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        stats[col] = {
            "count":  float(series.count()),
            "total":  round(float(series.sum()), 2),
            "mean":   round(float(series.mean()), 2),
            "median": round(float(series.median()), 2),
            "std":    round(float(series.std()), 2),
            "min":    round(float(series.min()), 2),
            "max":    round(float(series.max()), 2),
        }
    return stats


def compute_derived_stats(df: pd.DataFrame) -> dict[str, float | str]:
    """
    Compute derived nutritional ratios not available as raw columns.

    Currently computes:
    - ``fat_to_protein_ratio``: average fat(g) per gram of protein across all items
    - ``carb_to_protein_ratio``: average carbs(g) per gram of protein
    - ``calories_per_fat_g``: average calories per gram of fat
    - ``missing_columns``: comma-separated list of expected columns absent from *df*
      (e.g. ``"sugar_g, caffeine_mg"`` — not present in the source datasets)

    Returns
    -------
    dict
        Flat dict of ratio name → value (float) or note (str).
    """
    result: dict[str, float | str] = {}

    fat_g     = df["fat_g"].dropna()     if "fat_g"     in df.columns else None
    protein_g = df["protein_g"].dropna() if "protein_g" in df.columns else None
    carb_g    = df["carb_g"].dropna()    if "carb_g"    in df.columns else None
    calories  = df["calories"].dropna()  if "calories"  in df.columns else None

    if fat_g is not None and protein_g is not None:
        # Compute ratio on rows where both values exist and protein > 0
        both = df[["fat_g", "protein_g"]].dropna()
        both = both[both["protein_g"] > 0]
        result["fat_to_protein_ratio"] = round(float((both["fat_g"] / both["protein_g"]).mean()), 3)

    if carb_g is not None and protein_g is not None:
        both = df[["carb_g", "protein_g"]].dropna()
        both = both[both["protein_g"] > 0]
        result["carb_to_protein_ratio"] = round(float((both["carb_g"] / both["protein_g"]).mean()), 3)

    if calories is not None and fat_g is not None:
        both = df[["calories", "fat_g"]].dropna()
        both = both[both["fat_g"] > 0]
        result["calories_per_fat_g"] = round(float((both["calories"] / both["fat_g"]).mean()), 2)

    # Document columns that users might expect but are absent from the source data
    absent = [col for col in ("sugar_g", "caffeine_mg") if col not in df.columns]
    if absent:
        result["missing_columns"] = ", ".join(absent)

    return result


def compute_cross_dataset_stats(
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> dict[str, dict[str, float]]:
    """
    Compare per-column averages between the drinks and food datasets.

    Only columns present in *both* DataFrames are included.

    Returns
    -------
    dict
        ``{column_name: {"drinks_mean", "food_mean", "drinks_median", "food_median"}}``
    """
    shared = [
        c for c in SHARED_NUMERIC_COLS
        if c in drinks_df.columns and c in food_df.columns
    ]
    result: dict[str, dict[str, float]] = {}
    for col in shared:
        result[col] = {
            "drinks_mean":   round(float(drinks_df[col].mean(skipna=True)), 2),
            "food_mean":     round(float(food_df[col].mean(skipna=True)), 2),
            "drinks_median": round(float(drinks_df[col].median(skipna=True)), 2),
            "food_median":   round(float(food_df[col].median(skipna=True)), 2),
        }
    return result


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

# Maps each filter key to (dataframe column, comparison operator)
_FILTER_MAP: dict[str, tuple[str, str]] = {
    "max_calories":  ("calories",   "<="),
    "min_calories":  ("calories",   ">="),
    "max_fat_g":     ("fat_g",      "<="),
    "min_fat_g":     ("fat_g",      ">="),
    "max_carb_g":    ("carb_g",     "<="),
    "min_carb_g":    ("carb_g",     ">="),
    "max_fiber_g":   ("fiber_g",    "<="),
    "min_fiber_g":   ("fiber_g",    ">="),
    "max_protein_g": ("protein_g",  "<="),
    "min_protein_g": ("protein_g",  ">="),
    "max_sodium_mg": ("sodium_mg",  "<="),
    "min_sodium_mg": ("sodium_mg",  ">="),
}


def filter_by_criteria(
    df: pd.DataFrame,
    filters: dict[str, float],
) -> pd.DataFrame:
    """
    Filter *df* by one or more nutritional thresholds.

    Parameters
    ----------
    df:
        Cleaned DataFrame from :mod:`src.data_cleaner`.
    filters:
        ``{filter_key: threshold}`` — e.g. ``{"max_calories": 300,
        "min_protein_g": 10}``.  Unknown keys are silently ignored.
        Supported keys are the keys of :data:`_FILTER_MAP`.

    Returns
    -------
    pd.DataFrame
        Rows satisfying all supplied filters.  When a filter targets a column
        that contains NaN, those rows are excluded from the result.
    """
    mask = pd.Series(True, index=df.index)
    for key, threshold in filters.items():
        if key not in _FILTER_MAP:
            continue
        col, op = _FILTER_MAP[key]
        if col not in df.columns:
            continue
        if op == "<=":
            mask &= df[col].fillna(np.inf) <= threshold
        else:
            mask &= df[col].fillna(-np.inf) >= threshold
    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def get_top_n(
    df: pd.DataFrame,
    column: str,
    n: int = 10,
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Return the top *n* rows ranked by *column*.

    NaN values are excluded from ranking.

    Parameters
    ----------
    df:
        Cleaned DataFrame.
    column:
        Numeric column to sort by.
    n:
        Number of rows to return.
    ascending:
        ``True`` for lowest-first (e.g., least-caloric items).
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame.")
    return (
        df.dropna(subset=[column])
        .sort_values(column, ascending=ascending)
        .head(n)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def get_available_numeric_columns(df: pd.DataFrame) -> list[str]:
    """
    Return numeric columns present in *df*, in a consistent display order.

    Columns are ordered to match :data:`COLUMN_LABELS` first, then any
    additional numeric columns are appended at the end.  ``is_imputed`` is
    excluded as it is a boolean meta column, not a nutrient.
    """
    _EXCLUDE = {"is_imputed"}
    all_numeric = [
        c for c in df.select_dtypes(include="number").columns
        if c not in _EXCLUDE
    ]
    ordered = [c for c in COLUMN_LABELS if c in all_numeric]
    extras  = [c for c in all_numeric if c not in ordered]
    return ordered + extras


# ---------------------------------------------------------------------------
# Shared chart style
# ---------------------------------------------------------------------------

_FONT_FAMILY = "Inter, Arial, sans-serif"
_BG_COLOR    = "#FAFAFA"
_GRID_COLOR  = "#E5E5E5"

_MACRO_COLORS: dict[str, str] = {
    "fat_g":     "#EF476F",
    "carb_g":    "#FFD166",
    "protein_g": "#06D6A0",
}

_CATEGORY_PALETTE = px.colors.qualitative.Safe


def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    """Apply a consistent light theme to any figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, family=_FONT_FAMILY)),
        font=dict(family=_FONT_FAMILY, size=13),
        paper_bgcolor=_BG_COLOR,
        plot_bgcolor=_BG_COLOR,
        margin=dict(l=20, r=20, t=60, b=20),
        hoverlabel=dict(font_size=13, font_family=_FONT_FAMILY),
    )
    fig.update_xaxes(gridcolor=_GRID_COLOR, zerolinecolor=_GRID_COLOR)
    fig.update_yaxes(gridcolor=_GRID_COLOR, zerolinecolor=_GRID_COLOR)
    return fig


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def bar_chart_top_n(
    df: pd.DataFrame,
    column: str,
    n: int = 10,
    ascending: bool = False,
    title: str | None = None,
    color: str = "#00704A",
) -> go.Figure:
    """
    Horizontal bar chart of the top *n* items ranked by *column*.

    Parameters
    ----------
    df:
        Cleaned DataFrame.
    column:
        Nutrient column to rank by (e.g. ``"calories"``).
    n:
        Number of items to display.
    ascending:
        ``True`` shows lowest values first.
    color:
        Bar fill colour.
    """
    label      = COLUMN_LABELS.get(column, column)
    direction  = "Lowest" if ascending else "Highest"
    auto_title = title or f"Top {n} Items by {label} ({direction})"

    plot_df = (
        df.dropna(subset=[column])
        .sort_values(column, ascending=ascending)
        .head(n)
    )
    fig = px.bar(
        plot_df,
        x=column, y="item_name",
        orientation="h",
        text=column,
        labels={column: label, "item_name": ""},
        color_discrete_sequence=[color],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        marker_color=color,
    )
    fig.update_yaxes(categoryorder="total ascending" if not ascending else "total descending")
    return _base_layout(fig, auto_title)


def stacked_macro_bar(
    df: pd.DataFrame,
    n: int = 15,
    sort_by: str = "calories",
    title: str | None = None,
) -> go.Figure:
    """
    Stacked horizontal bar showing fat / carbs / protein per item.

    Best chart for comparing nutritional *composition* across items — you can
    immediately see which items are carb-heavy vs protein-rich vs fat-dense.

    Parameters
    ----------
    df:
        Cleaned DataFrame.
    n:
        Number of items to include, selected by *sort_by* descending.
    sort_by:
        Column used to rank and select the top *n* items.
    """
    macros     = [c for c in ("fat_g", "carb_g", "protein_g") if c in df.columns]
    auto_title = title or f"Macronutrient Composition — Top {n} Items"

    plot_df = (
        df.dropna(subset=macros)
        .sort_values(sort_by, ascending=False)
        .head(n)[["item_name"] + macros]
        .melt(id_vars="item_name", value_vars=macros, var_name="macro", value_name="grams")
    )
    plot_df["macro_label"] = plot_df["macro"].map({
        "fat_g": "Fat (g)", "carb_g": "Carbs (g)", "protein_g": "Protein (g)",
    })
    fig = px.bar(
        plot_df,
        x="grams", y="item_name",
        color="macro_label",
        orientation="h",
        labels={"grams": "Grams", "item_name": "", "macro_label": "Macro"},
        color_discrete_map={
            "Fat (g)":     _MACRO_COLORS["fat_g"],
            "Carbs (g)":   _MACRO_COLORS["carb_g"],
            "Protein (g)": _MACRO_COLORS["protein_g"],
        },
        barmode="stack",
    )
    fig.update_yaxes(categoryorder="total ascending")
    return _base_layout(fig, auto_title)


def grouped_comparison_bar(
    cross_stats: dict[str, dict[str, float]],
    metric: str = "mean",
    title: str = "Average Nutrition: Drinks vs Food",
) -> go.Figure:
    """
    Side-by-side grouped bar comparing drinks and food for each shared nutrient.

    Parameters
    ----------
    cross_stats:
        Output of :func:`compute_cross_dataset_stats`.
    metric:
        ``"mean"`` or ``"median"``.
    """
    drinks_vals, food_vals, cols = [], [], []
    for col, vals in cross_stats.items():
        key_d, key_f = f"drinks_{metric}", f"food_{metric}"
        if key_d in vals and key_f in vals:
            cols.append(COLUMN_LABELS.get(col, col))
            drinks_vals.append(vals[key_d])
            food_vals.append(vals[key_f])

    fig = go.Figure(data=[
        go.Bar(
            name="Drinks",
            x=cols, y=drinks_vals,
            marker_color="#00704A",
            text=[f"{v:.1f}" for v in drinks_vals],
            textposition="outside",
        ),
        go.Bar(
            name="Food",
            x=cols, y=food_vals,
            marker_color="#CBA258",
            text=[f"{v:.1f}" for v in food_vals],
            textposition="outside",
        ),
    ])
    fig.update_layout(barmode="group", yaxis_title="Value", xaxis_title="")
    return _base_layout(fig, title)


def pie_chart_macro(
    item_row: pd.Series,
    title: str | None = None,
) -> go.Figure | None:
    """
    Donut pie chart of fat / carbs / protein for one menu item.

    Returns ``None`` if all macro values are NaN or zero.

    Parameters
    ----------
    item_row:
        A single row from a cleaned DataFrame (e.g. ``df.iloc[0]``).
    """
    macro_map = {
        "Fat (g)":     item_row.get("fat_g"),
        "Carbs (g)":   item_row.get("carb_g"),
        "Protein (g)": item_row.get("protein_g"),
    }
    macro_map = {k: v for k, v in macro_map.items() if v and not pd.isna(v) and v > 0}
    if not macro_map:
        return None

    auto_title = title or f"Macronutrient Breakdown: {item_row.get('item_name', '')}"
    fig = px.pie(
        names=list(macro_map.keys()),
        values=list(macro_map.values()),
        color=list(macro_map.keys()),
        color_discrete_map={
            "Fat (g)":     _MACRO_COLORS["fat_g"],
            "Carbs (g)":   _MACRO_COLORS["carb_g"],
            "Protein (g)": _MACRO_COLORS["protein_g"],
        },
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _base_layout(fig, auto_title)


def scatter_nutrition(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str = "source",
    title: str | None = None,
) -> go.Figure:
    """
    Interactive scatter of two nutritional metrics across items.

    Hover shows the item name and exact values.  Points are coloured by
    *color_col* (e.g. ``"source"`` for drinks/food split, or ``"category"``
    to compare drink categories).

    Parameters
    ----------
    df:
        Cleaned DataFrame; can be the combined drinks + food DataFrame.
    x_col:
        Nutrient column for the x-axis.
    y_col:
        Nutrient column for the y-axis.
    color_col:
        Categorical column used to colour points.
    """
    x_label    = COLUMN_LABELS.get(x_col, x_col)
    y_label    = COLUMN_LABELS.get(y_col, y_col)
    auto_title = title or f"{x_label} vs {y_label}"

    plot_df = df.dropna(subset=[x_col, y_col]).copy()
    fig = px.scatter(
        plot_df,
        x=x_col, y=y_col,
        color=color_col,
        hover_name="item_name",
        hover_data={x_col: ":.1f", y_col: ":.1f", color_col: False},
        labels={x_col: x_label, y_col: y_label, color_col: color_col.capitalize()},
        color_discrete_sequence=_CATEGORY_PALETTE,
        opacity=0.8,
    )
    fig.update_traces(marker=dict(size=9, line=dict(width=0.5, color="white")))
    return _base_layout(fig, auto_title)


def histogram_distribution(
    df: pd.DataFrame,
    column: str,
    color_col: str = "source",
    nbins: int = 30,
    title: str | None = None,
) -> go.Figure:
    """
    Histogram with a box-plot marginal for a single nutritional column.

    The combined histogram + box gives distribution shape and outliers at a glance.

    Parameters
    ----------
    df:
        Cleaned DataFrame.
    column:
        Nutrient column to plot.
    color_col:
        Column used to colour bars (e.g. ``"source"``).
    nbins:
        Number of histogram bins.
    """
    label      = COLUMN_LABELS.get(column, column)
    auto_title = title or f"Distribution of {label}"
    plot_df    = df.dropna(subset=[column])

    fig = px.histogram(
        plot_df,
        x=column,
        color=color_col,
        nbins=nbins,
        marginal="box",
        labels={column: label, color_col: color_col.capitalize()},
        color_discrete_sequence=_CATEGORY_PALETTE,
        barmode="overlay",
        opacity=0.75,
    )
    return _base_layout(fig, auto_title)


def category_box_plot(
    df: pd.DataFrame,
    column: str,
    title: str | None = None,
) -> go.Figure:
    """
    Box plot showing the spread of *column* across drink categories.

    Useful for understanding how calorie or macro ranges differ between
    Lattes, Frappuccinos, Teas, etc.

    Parameters
    ----------
    df:
        Cleaned drinks DataFrame with a ``category`` column.
    column:
        Nutrient column to compare across categories.
    """
    label      = COLUMN_LABELS.get(column, column)
    auto_title = title or f"{label} by Drink Category"
    plot_df    = df.dropna(subset=[column])

    order = (
        plot_df.groupby("category")[column]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    fig = px.box(
        plot_df,
        x="category", y=column,
        color="category",
        category_orders={"category": order},
        points="outliers",
        labels={"category": "Category", column: label},
        color_discrete_sequence=_CATEGORY_PALETTE,
    )
    fig.update_layout(showlegend=False)
    return _base_layout(fig, auto_title)
