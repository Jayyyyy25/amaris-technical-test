"""
Overview page — dataset stats, data quality report, raw data explorer.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processor import (
    compute_descriptive_stats,
    compute_derived_stats,
    filter_by_criteria,
    COLUMN_LABELS,
)


def render() -> None:
    st.header("📊 Dataset Overview")

    drinks_df = st.session_state.get("drinks_df")
    food_df   = st.session_state.get("food_df")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    # Apply filters
    filters   = st.session_state.get("filters", {})
    d_filtered = filter_by_criteria(drinks_df, filters) if filters else drinks_df
    f_filtered = filter_by_criteria(food_df,   filters) if filters else food_df

    # ── Top-level metrics ────────────────────────────────────────────────────
    st.subheader("At a Glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Drinks (total)",        len(drinks_df))
    c2.metric("Food items (total)",    len(food_df))
    c3.metric("Drinks with imputed values",
              int(drinks_df["is_imputed"].sum()) if "is_imputed" in drinks_df.columns else 0)
    c4.metric("After current filters", f"{len(d_filtered)} drinks · {len(f_filtered)} food")

    st.divider()

    # ── Data quality note ────────────────────────────────────────────────────
    n_imputed = int(drinks_df["is_imputed"].sum()) if "is_imputed" in drinks_df.columns else 0
    pct = round(n_imputed / len(drinks_df) * 100, 1) if len(drinks_df) else 0

    with st.expander("ℹ️ Data Quality & Cleaning Steps", expanded=True):
        st.markdown(f"""
**Drinks dataset**
- `{len(drinks_df)}` items loaded after duplicate removal.
- `{n_imputed}` items ({pct}%) had missing numeric values (stored as `-` in the source file).
  These were **imputed using per-category medians** (Latte, Frappuccino, Tea, etc.) rather than dropped,
  preserving all rows for analysis.
- Fallback to global column median when a category had no complete rows for that column.

**Food dataset**
- `{len(food_df)}` items loaded. No missing values; no imputation required.
- File encoded as UTF-16 LE with BOM — handled automatically.

**Both datasets**
- Column names normalised to `snake_case` (e.g. `Fat (g)` → `fat_g`).
- Duplicate item names removed (keep first occurrence).
- ⚠️ **Caffeine and sugar data are not present** in either dataset.
""")

    st.divider()

    # ── Descriptive statistics ───────────────────────────────────────────────
    st.subheader("Descriptive Statistics")

    col_left, col_right = st.columns(2)

    def _stats_table(df: pd.DataFrame, label: str, col) -> None:
        stats = compute_descriptive_stats(df)
        rows = []
        for col_name, s in stats.items():
            rows.append({
                "Nutrient": COLUMN_LABELS.get(col_name, col_name),
                "Mean":     s["mean"],
                "Median":   s["median"],
                "Min":      s["min"],
                "Max":      s["max"],
                "Total":    s["total"],
            })
        col.markdown(f"**{label}**")
        col.dataframe(pd.DataFrame(rows).set_index("Nutrient"), use_container_width=True)

    _stats_table(d_filtered, f"Drinks ({len(d_filtered)} items)", col_left)
    _stats_table(f_filtered, f"Food ({len(f_filtered)} items)",   col_right)

    st.divider()

    # ── Derived ratios ───────────────────────────────────────────────────────
    st.subheader("Derived Nutritional Ratios")

    d_derived = compute_derived_stats(d_filtered)
    f_derived = compute_derived_stats(f_filtered)

    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Drinks — Fat:Protein",  d_derived.get("fat_to_protein_ratio",  "N/A"))
    rc2.metric("Drinks — Carb:Protein", d_derived.get("carb_to_protein_ratio", "N/A"))
    rc3.metric("Food — Fat:Protein",    f_derived.get("fat_to_protein_ratio",  "N/A"))
    rc4.metric("Food — Carb:Protein",   f_derived.get("carb_to_protein_ratio", "N/A"))

    st.divider()

    # ── Category breakdown (drinks only) ────────────────────────────────────
    if "category" in drinks_df.columns:
        st.subheader("Drinks by Category")

        cat_counts   = drinks_df["category"].value_counts()
        cat_imputed  = (
            drinks_df[drinks_df["is_imputed"]]["category"].value_counts()
            if "is_imputed" in drinks_df.columns
            else pd.Series(dtype=int)
        )
        cat_df = pd.DataFrame({
            "Items":        cat_counts,
            "Imputed":      cat_imputed,
        }).fillna(0).astype({"Items": int, "Imputed": int})
        cat_df["Imputed %"] = (cat_df["Imputed"] / cat_df["Items"] * 100).round(1)
        st.dataframe(cat_df, use_container_width=True)

    st.divider()

    # ── Raw data explorer ────────────────────────────────────────────────────
    with st.expander("🔎 Explore Raw Data"):
        dataset_choice = st.radio("Dataset", ["Drinks", "Food"], horizontal=True)
        show_df = d_filtered if dataset_choice == "Drinks" else f_filtered
        st.dataframe(show_df, use_container_width=True, height=400)
        st.caption(f"{len(show_df)} rows shown (filters applied)")
