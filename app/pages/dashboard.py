"""
Dashboard page — styled summary banner, metric cards, key charts.
"""

from __future__ import annotations

import streamlit as st

from src.data_processor import (
    compute_descriptive_stats,
    compute_derived_stats,
    compute_cross_dataset_stats,
    bar_chart_top_n,
    category_box_plot,
    grouped_comparison_bar,
    COLUMN_LABELS,
)



def _metric_card(title: str, icon: str,
                 d_val: str, d_unit: str,
                 f_val: str, f_unit: str,
                 note: str = "", note_positive: bool = True) -> str:
    delta_cls = "metric-delta-pos" if note_positive else "metric-delta-neu"
    note_html = f'<div class="{delta_cls}">{note}</div>' if note else ""
    return f"""
<div class="metric-card">
  <div class="metric-card-title">{title}<span class="metric-card-icon">{icon}</span></div>
  <div class="metric-values">
    <div class="metric-col">
      <span class="metric-label">Drinks</span>
      <span class="metric-value">{d_val}<span class="metric-unit">{d_unit}</span></span>
    </div>
    <div class="metric-col">
      <span class="metric-label">Food</span>
      <span class="metric-value">{f_val}<span class="metric-unit">{f_unit}</span></span>
    </div>
  </div>
  {note_html}
</div>
"""


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render() -> None:
    # ── Page header with branding ────────────────────────────────────────────
    st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin:20px;">
  <div style="width:48px;height:48px;background:#2a8848;border-radius:12px;
              display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">
    ☕
  </div>
  <div>
    <p style="margin:0;font-size:22px;font-weight:800;color:#1a1a1a;line-height:1.2;">
      Starbucks Nutrition
    </p>
    <p style="margin:0;font-size:11px;font-weight:700;color:#2a8848;
              text-transform:uppercase;letter-spacing:1.3px;">
      Analysis Tool
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    drinks_df   = st.session_state.get("drinks_df")
    food_df     = st.session_state.get("food_df")
    groq_client = st.session_state.get("groq_client")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    d_stats   = compute_descriptive_stats(drinks_df)
    f_stats   = compute_descriptive_stats(food_df)
    d_derived = compute_derived_stats(drinks_df)
    f_derived = compute_derived_stats(food_df)

    # ── AI Summary Banner ────────────────────────────────────────────────────
    brief = st.session_state.get("brief_summary")
    llm_ok = groq_client is not None and groq_client.is_available()

    if brief:
        st.markdown(f"""
<div class="summary-banner">
  <div class="summary-badge">AI Summary</div>
  <p class="summary-title">Current Nutritional Snapshot</p>
  <p class="summary-text">{brief}</p>
</div>
""", unsafe_allow_html=True)
        col_exp, col_dl = st.columns([3, 1])
        with col_exp:
            with st.expander("Read full detailed report"):
                full = st.session_state.get("llm_summary")
                if full:
                    st.markdown(full)
                else:
                    if st.button("Generate full report", key="gen_full"):
                        with st.spinner("Generating full report…"):
                            try:
                                from src.summarizer import generate_summary
                                st.session_state.llm_summary = generate_summary(
                                    groq_client, drinks_df, food_df
                                )
                                st.rerun()
                            except RuntimeError as exc:
                                st.error(str(exc))
        with col_dl:
            full = st.session_state.get("llm_summary")
            if full:
                st.download_button(
                    "Download Full Report",
                    data=full,
                    file_name="starbucks_nutrition_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
    else:
        if llm_ok:
            st.markdown("""
<div class="summary-banner">
  <div class="summary-badge">AI Summary</div>
  <p class="summary-title">Current Nutritional Snapshot</p>
  <p class="summary-text" style="opacity:0.7;font-style:italic;">
    Click below to generate an AI-powered summary of both datasets.
  </p>
</div>
""", unsafe_allow_html=True)
            if st.button("Generate AI Summary", type="primary"):
                with st.spinner("Generating summary…"):
                    try:
                        from src.summarizer import generate_brief_summary, generate_summary
                        st.session_state.brief_summary = generate_brief_summary(
                            groq_client, drinks_df, food_df
                        )
                        st.session_state.llm_summary = generate_summary(
                            groq_client, drinks_df, food_df
                        )
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))
        else:
            st.markdown("""
<div class="summary-banner">
  <div class="summary-badge">AI Summary</div>
  <p class="summary-title">Current Nutritional Snapshot</p>
  <p class="summary-text" style="opacity:0.7;font-style:italic;">
    Connect the LLM in the sidebar to generate an AI-powered summary.
  </p>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── Metric Cards ─────────────────────────────────────────────────────────
    def _s(stats: dict, col: str, decimals: int = 0) -> str:
        if col not in stats:
            return "N/A"
        v = stats[col]["mean"]
        return f"{v:.{decimals}f}"

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(_metric_card(
            "Avg Calories", "🔥",
            _s(d_stats, "calories"), " kcal",
            _s(f_stats, "calories"), " kcal",
            note=f"Food is {round(f_stats['calories']['mean'] / d_stats['calories']['mean'], 1)}× higher"
                 if "calories" in d_stats and d_stats["calories"]["mean"] > 0 else "",
            note_positive=False,
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(_metric_card(
            "Avg Protein", "💪",
            _s(d_stats, "protein_g", 1), " g",
            _s(f_stats, "protein_g", 1), " g",
            note=f"Avg fat {_s(d_stats, 'fat_g', 1)} g (drinks) · {_s(f_stats, 'fat_g', 1)} g (food)",
            note_positive=True,
        ), unsafe_allow_html=True)

    with c3:
        d_ratio = d_derived.get("fat_to_protein_ratio", "N/A")
        f_ratio = f_derived.get("fat_to_protein_ratio", "N/A")
        st.markdown(_metric_card(
            "Fat-to-Protein Ratio", "⚖️",
            str(d_ratio), " ratio",
            str(f_ratio), " ratio",
            note="Healthy threshold: ≤ 1.5",
            note_positive=False,
        ), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── Chart Section ─────────────────────────────────────────────────────────
    st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Caloric Density by Category</div>
  <div class="chart-card-subtitle">Average calories per serving across drink categories and food</div>
</div>
""", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)

    chart_type = st.segmented_control(
        "Chart type",
        options=["Bar Chart", "Box Plot"],
        default="Bar Chart",
        label_visibility="collapsed",
    )

    if chart_type == "Bar Chart":
        if "category" in drinks_df.columns:
            import plotly.express as px
            cat_means = (
                drinks_df.groupby("category")["calories"]
                .mean()
                .reset_index()
                .rename(columns={"calories": "Avg Calories", "category": "Category"})
                .sort_values("Avg Calories", ascending=False)
            )
            fig = px.bar(
                cat_means, x="Category", y="Avg Calories",
                color="Category",
                text="Avg Calories",
                labels={"Avg Calories": "Avg Calories (kcal)"},
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(
                showlegend=False,
                paper_bgcolor="#FAFAFA",
                plot_bgcolor="#FAFAFA",
                margin=dict(l=10, r=10, t=20, b=10),
                font=dict(family="Inter, Arial, sans-serif"),
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#E5E5E5")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.plotly_chart(
            category_box_plot(drinks_df, "calories"),
            use_container_width=True,
        )

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── Second chart row ──────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Top 10 Highest-Calorie Drinks</div>
  <div class="chart-card-subtitle">Items ranked by calorie content</div>
</div>
""", unsafe_allow_html=True)
        st.plotly_chart(
            bar_chart_top_n(drinks_df, "calories", n=10),
            use_container_width=True,
        )
    with col_r:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Avg Nutrition: Drinks vs Food</div>
  <div class="chart-card-subtitle">Mean values across shared nutrients</div>
</div>
""", unsafe_allow_html=True)
        cross = compute_cross_dataset_stats(drinks_df, food_df)
        st.plotly_chart(
            grouped_comparison_bar(cross, "calories"),
            use_container_width=True,
        )
