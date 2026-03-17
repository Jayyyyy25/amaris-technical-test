"""
Visualizations page — interactive Plotly charts for nutritional exploration.
"""

from __future__ import annotations

import streamlit as st

from src.data_processor import (
    bar_chart_top_n,
    stacked_macro_bar,
    grouped_comparison_bar,
    pie_chart_macro,
    scatter_nutrition,
    histogram_distribution,
    category_box_plot,
    compute_cross_dataset_stats,
    filter_by_criteria,
    get_top_n,
    get_available_numeric_columns,
    COLUMN_LABELS,
)


def render() -> None:
    st.header("📈 Visualizations")

    drinks_df = st.session_state.get("drinks_df")
    food_df   = st.session_state.get("food_df")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    filters    = st.session_state.get("filters", {})
    d_filtered = filter_by_criteria(drinks_df, filters) if filters else drinks_df
    f_filtered = filter_by_criteria(food_df,   filters) if filters else food_df

    # ── Section 1: Top-N by nutrient ─────────────────────────────────────────
    st.subheader("1 · Top Items by Nutrient")

    s1c1, s1c2, s1c3, s1c4 = st.columns([2, 2, 1, 1])
    s1_dataset   = s1c1.selectbox("Dataset",   ["Drinks", "Food"], key="s1_ds")
    s1_df        = d_filtered if s1_dataset == "Drinks" else f_filtered
    s1_avail     = get_available_numeric_columns(s1_df)
    s1_col       = s1c2.selectbox(
        "Nutrient",
        s1_avail,
        format_func=lambda c: COLUMN_LABELS.get(c, c),
        key="s1_col",
    )
    s1_n         = s1c3.number_input("Top N", 5, 20, 10, key="s1_n")
    s1_direction = s1c4.selectbox("Direction", ["Highest", "Lowest"], key="s1_dir")
    ascending    = s1_direction == "Lowest"

    st.plotly_chart(
        bar_chart_top_n(s1_df, s1_col, n=int(s1_n), ascending=ascending),
        use_container_width=True,
    )

    st.divider()

    # ── Section 2: Macro composition ─────────────────────────────────────────
    st.subheader("2 · Macronutrient Composition")

    s2c1, s2c2, s2c3 = st.columns([2, 1, 1])
    s2_dataset = s2c1.selectbox("Dataset", ["Drinks", "Food"], key="s2_ds")
    s2_df      = d_filtered if s2_dataset == "Drinks" else f_filtered
    s2_n       = s2c2.number_input("Items to show", 5, 30, 15, key="s2_n")
    s2_avail   = get_available_numeric_columns(s2_df)
    s2_sort    = s2c3.selectbox(
        "Sort by",
        s2_avail,
        format_func=lambda c: COLUMN_LABELS.get(c, c),
        key="s2_sort",
    )

    st.plotly_chart(
        stacked_macro_bar(s2_df, n=int(s2_n), sort_by=s2_sort),
        use_container_width=True,
    )

    st.divider()

    # ── Section 3: Drinks vs Food comparison ─────────────────────────────────
    st.subheader("3 · Drinks vs Food Comparison")

    cross_stats = compute_cross_dataset_stats(d_filtered, f_filtered)
    shared_cols = list(cross_stats.keys())

    if shared_cols:
        s3_metric = st.selectbox(
            "Metric",
            shared_cols,
            format_func=lambda c: COLUMN_LABELS.get(c, c),
            key="s3_metric",
        )
        st.plotly_chart(
            grouped_comparison_bar(cross_stats, s3_metric),
            use_container_width=True,
        )
    else:
        st.warning("No shared numeric columns between the two datasets.")

    st.divider()

    # ── Section 4: Per-item macro pie ─────────────────────────────────────────
    st.subheader("4 · Macro Breakdown for a Single Item")

    s4c1, s4c2 = st.columns([2, 1])
    s4_dataset = s4c1.selectbox("Dataset", ["Drinks", "Food"], key="s4_ds")
    s4_df      = d_filtered if s4_dataset == "Drinks" else f_filtered

    item_names = s4_df["item_name"].dropna().sort_values().tolist()
    selected   = s4c2.selectbox("Item", item_names, key="s4_item") if item_names else None

    if selected:
        row = s4_df[s4_df["item_name"] == selected].iloc[0]
        fig = pie_chart_macro(row, title=selected)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No macro data available for this item.")

    st.divider()

    # ── Section 5: Scatter — two nutrients ───────────────────────────────────
    st.subheader("5 · Nutrient Correlation Scatter")

    s5c1, s5c2, s5c3 = st.columns([2, 2, 2])
    s5_dataset = s5c1.selectbox("Dataset", ["Drinks", "Food"], key="s5_ds")
    s5_df      = d_filtered if s5_dataset == "Drinks" else f_filtered
    s5_avail   = get_available_numeric_columns(s5_df)

    s5_x = s5c2.selectbox(
        "X axis", s5_avail,
        format_func=lambda c: COLUMN_LABELS.get(c, c),
        key="s5_x",
    )
    s5_y_default = s5_avail[1] if len(s5_avail) > 1 else s5_avail[0]
    s5_y = s5c3.selectbox(
        "Y axis", s5_avail,
        index=s5_avail.index(s5_y_default),
        format_func=lambda c: COLUMN_LABELS.get(c, c),
        key="s5_y",
    )
    color_col = "category" if "category" in s5_df.columns else None

    st.plotly_chart(
        scatter_nutrition(s5_df, s5_x, s5_y, color_col=color_col),
        use_container_width=True,
    )

    st.divider()

    # ── Section 6: Distribution histogram ────────────────────────────────────
    st.subheader("6 · Nutrient Distribution")

    s6c1, s6c2, s6c3 = st.columns([2, 2, 1])
    s6_dataset = s6c1.selectbox("Dataset", ["Drinks", "Food"], key="s6_ds")
    s6_df      = d_filtered if s6_dataset == "Drinks" else f_filtered
    s6_avail   = get_available_numeric_columns(s6_df)
    s6_col     = s6c2.selectbox(
        "Nutrient", s6_avail,
        format_func=lambda c: COLUMN_LABELS.get(c, c),
        key="s6_col",
    )
    s6_bins    = s6c3.number_input("Bins", 10, 100, 30, key="s6_bins")

    st.plotly_chart(
        histogram_distribution(s6_df, s6_col, nbins=int(s6_bins)),
        use_container_width=True,
    )

    st.divider()

    # ── Section 7: Category box plot (drinks only) ────────────────────────────
    st.subheader("7 · Nutrient Distribution by Drink Category")

    if "category" not in drinks_df.columns:
        st.info("Category data is only available for drinks.")
    else:
        s7c1, _ = st.columns([2, 3])
        s7_avail = get_available_numeric_columns(d_filtered)
        s7_col   = s7c1.selectbox(
            "Nutrient", s7_avail,
            format_func=lambda c: COLUMN_LABELS.get(c, c),
            key="s7_col",
        )
        st.plotly_chart(
            category_box_plot(d_filtered, s7_col),
            use_container_width=True,
        )
