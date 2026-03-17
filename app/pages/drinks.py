"""
Drinks Analysis page.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processor import (
    compute_descriptive_stats,
    compute_derived_stats,
    get_available_numeric_columns,
    bar_chart_top_n,
    scatter_nutrition,
    COLUMN_LABELS,
)


def _metric_card(title: str, icon: str, value: str, unit: str,
                 note: str = "", note_positive: bool = True) -> str:
    delta_cls = "metric-delta-pos" if note_positive else "metric-delta-neu"
    note_html = f'<div class="{delta_cls}">{note}</div>' if note else ""
    return f"""
<div class="metric-card">
  <div class="metric-card-title">{title}<span class="metric-card-icon">{icon}</span></div>
  <div class="metric-values">
    <div class="metric-col">
      <span class="metric-value">{value}<span class="metric-unit"> {unit}</span></span>
    </div>
  </div>
  {note_html}
</div>
"""


def render() -> None:
    drinks_df = st.session_state.get("drinks_df")
    if drinks_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    groq_client = st.session_state.get("groq_client")

    # ── Header ────────────────────────────────────────────────────────────────
    col_title, col_export = st.columns([5, 1])
    with col_title:
        st.markdown(
            '<h2 style="margin:0 0 4px 0;font-size:26px;font-weight:800;color:#1a1a1a;">'
            'Drink Nutrition Analysis</h2>',
            unsafe_allow_html=True,
        )
    with col_export:
        st.download_button(
            "⬇ Export Data",
            drinks_df.to_csv(index=False).encode(),
            file_name="drinks.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Quick Filters ─────────────────────────────────────────────────────────
    cal_max = int(drinks_df["calories"].max()) if "calories" in drinks_df.columns else 1000

    qf1, qf2 = st.columns([3, 2])
    with qf1:
        st.markdown('<p class="filter-label">Quick Filters</p>', unsafe_allow_html=True)
        active_pills = st.pills(
            "drinks_quick_filters",
            ["⚡ High Protein", "🌿 Low Calorie", "🧂 Low Sodium"],
            selection_mode="multi",
            label_visibility="collapsed",
            key="d_pills",
        )
    with qf2:
        cal_range = st.slider(
            "Calorie Range (kcal)", 0, cal_max, (0, cal_max), key="d_cal_range",
        )

    # Apply filters
    df = drinks_df.copy()
    if active_pills:
        if "⚡ High Protein" in active_pills and "protein_g" in df.columns:
            df = df[df["protein_g"] > 5]
        if "🌿 Low Calorie" in active_pills and "calories" in df.columns:
            df = df[df["calories"] < 150]
        if "🧂 Low Sodium" in active_pills and "sodium_mg" in df.columns:
            df = df[df["sodium_mg"] < 200]
    if "calories" in df.columns:
        df = df[(df["calories"] >= cal_range[0]) & (df["calories"] <= cal_range[1])]
    df = df.reset_index(drop=True)

    st.caption(f"Showing **{len(df)}** of {len(drinks_df)} drinks")

    # ── Metric Cards ──────────────────────────────────────────────────────────
    stats   = compute_descriptive_stats(df)
    derived = compute_derived_stats(df)

    def _s(col: str, key: str = "mean", dec: int = 0) -> str:
        if col not in stats:
            return "N/A"
        return f"{stats[col][key]:.{dec}f}"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_metric_card("Avg Calories", "🔥", _s("calories"), "kcal"), unsafe_allow_html=True)
    with c2:
        st.markdown(_metric_card("Median Fat", "🧈", _s("fat_g", "median", 1), "g"), unsafe_allow_html=True)
    with c3:
        st.markdown(_metric_card("Avg Protein", "💪", _s("protein_g", "mean", 1), "g"), unsafe_allow_html=True)
    with c4:
        ratio = derived.get("fat_to_protein_ratio", "N/A")
        is_ok = isinstance(ratio, (int, float)) and ratio <= 1.5
        st.markdown(_metric_card(
            "Fat:Protein Ratio", "⚖️", str(ratio), "",
            note="✓ Within healthy threshold" if is_ok else "⚠ Above healthy threshold",
            note_positive=is_ok,
        ), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # ── AI Insight ────────────────────────────────────────────────────────────
    llm_ok     = groq_client is not None and groq_client.is_available()
    insight    = st.session_state.get("drinks_insight")

    if llm_ok:
        if insight:
            st.markdown(f"""
<div class="insight-card">
  <div>
    <div class="insight-title">✦ AI Insights Summary</div>
    <p class="insight-text">{insight}</p>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            if st.button("✦ Generate AI Insight", key="d_gen_insight"):
                with st.spinner("Generating insight…"):
                    try:
                        from src.summarizer import answer_query
                        food_df = st.session_state.get("food_df", pd.DataFrame())
                        st.session_state["drinks_insight"] = answer_query(
                            groq_client,
                            "In 2 sentences, highlight the most notable nutritional patterns in the drinks data.",
                            df, food_df,
                        )
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))

    # ── Charts ────────────────────────────────────────────────────────────────
    avail = get_available_numeric_columns(df)
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Calories by Category</div>
  <div class="chart-card-subtitle">Average calories per drink category</div>
</div>
""", unsafe_allow_html=True)
        if "category" in df.columns and not df.empty:
            import plotly.express as px
            cat_means = (
                df.groupby("category")["calories"]
                .mean()
                .reset_index()
                .rename(columns={"calories": "Avg Calories", "category": "Category"})
                .sort_values("Avg Calories", ascending=True)
            )
            fig = px.bar(
                cat_means, x="Avg Calories", y="Category",
                orientation="h", text="Avg Calories",
                color_discrete_sequence=["#00704A"],
            )
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(
                showlegend=False,
                paper_bgcolor="#FAFAFA", plot_bgcolor="#FAFAFA",
                margin=dict(l=10, r=40, t=20, b=10),
                font=dict(family="Inter, Arial, sans-serif"),
                xaxis_title="Avg Calories (kcal)", yaxis_title="",
            )
            fig.update_xaxes(gridcolor="#E5E5E5")
            fig.update_yaxes(showgrid=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.plotly_chart(bar_chart_top_n(df, "calories", n=10), use_container_width=True)

    with ch2:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Fat vs Protein</div>
  <div class="chart-card-subtitle">Nutrient relationship by category</div>
</div>
""", unsafe_allow_html=True)
        x_col = "fat_g"     if "fat_g"     in avail else avail[0]
        y_col = "protein_g" if "protein_g" in avail else (avail[1] if len(avail) > 1 else avail[0])
        st.plotly_chart(
            scatter_nutrition(df, x_col, y_col,
                              color_col="category" if "category" in df.columns else None),
            use_container_width=True,
        )

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── Inventory Table ───────────────────────────────────────────────────────
    inv_l, inv_r = st.columns([4, 1])
    with inv_l:
        st.markdown(
            '<h3 style="font-size:20px;font-weight:700;color:#1a1a1a;margin:0 0 8px 0;">'
            'Drink Inventory</h3>',
            unsafe_allow_html=True,
        )
    with inv_r:
        st.caption(f"Showing {len(df)} drinks")

    display_cols = [c for c in
                    ["item_name", "category", "calories", "fat_g", "carb_g", "protein_g", "sodium_mg"]
                    if c in df.columns]
    rename_map = {c: COLUMN_LABELS.get(c, c) for c in display_cols}
    rename_map["item_name"] = "Drink Name"
    rename_map["category"]  = "Category"

    display_df = df[display_cols].rename(columns=rename_map)

    def _highlight(col: pd.Series):
        if col.dtype == object:
            return [""] * len(col)
        med, std = col.median(), col.std()
        result = []
        for v in col:
            if pd.isna(v):
                result.append("")
            elif v > med + std:
                result.append("color: #dc2626; font-weight: 600")
            elif v < med - std:
                result.append("color: #16a34a; font-weight: 600")
            else:
                result.append("")
        return result

    st.dataframe(
        display_df.style.apply(_highlight),
        use_container_width=True,
        height=420,
    )
