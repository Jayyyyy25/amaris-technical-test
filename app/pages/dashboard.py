"""
Dashboard page — styled summary banner, metric cards, key charts.
"""

from __future__ import annotations

import streamlit as st

from src.data.processor import compute_descriptive_stats, compute_derived_stats
from app.components.cards import metric_card_dual
from app.components.ui import (
    ai_powered_badge,
    ai_ready_badge,
    chart_header,
    page_header_card,
    spacer,
    summary_banner_disconnected,
    summary_banner_prompt,
    summary_banner_with_content,
)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render() -> None:
    groq_client = st.session_state.get("groq_client")
    brief       = st.session_state.get("brief_summary")
    llm_ok      = groq_client is not None and groq_client.is_available()

    # ── Page header ───────────────────────────────────────────────────────────
    hdr_l, hdr_r = st.columns([5, 1], vertical_alignment="center")
    with hdr_l:
        st.markdown(page_header_card(), unsafe_allow_html=True)
    with hdr_r:
        if brief:
            st.markdown(ai_ready_badge(), unsafe_allow_html=True)
        elif llm_ok:
            if st.button("✦ Generate", use_container_width=True):
                st.session_state["_generate_summary"] = True
        else:
            st.markdown(ai_powered_badge(), unsafe_allow_html=True)

    drinks_df = st.session_state.get("drinks_df")
    food_df   = st.session_state.get("food_df")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    d_stats   = compute_descriptive_stats(drinks_df)
    f_stats   = compute_descriptive_stats(food_df)
    d_derived = compute_derived_stats(drinks_df)
    f_derived = compute_derived_stats(food_df)

    # ── Deferred summary generation (runs at full width, outside header columns) ──
    if st.session_state.pop("_generate_summary", False):
        with st.spinner("Generating summary…"):
            try:
                from src.llm.summarizer import generate_brief_summary, generate_summary
                st.session_state.brief_summary = generate_brief_summary(
                    groq_client, drinks_df, food_df,
                )
                st.session_state.llm_summary = generate_summary(
                    groq_client, drinks_df, food_df,
                )
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    # ── AI Summary Banner ────────────────────────────────────────────────────
    brief  = st.session_state.get("brief_summary")
    llm_ok = groq_client is not None and groq_client.is_available()

    if brief:
        st.markdown(summary_banner_with_content(brief), unsafe_allow_html=True)
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
                                from src.llm.summarizer import generate_summary
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
                    "⬇ Download Report",
                    data=full,
                    file_name="starbucks_nutrition_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
    elif llm_ok:
        st.markdown(summary_banner_prompt(), unsafe_allow_html=True)
    else:
        st.markdown(summary_banner_disconnected(), unsafe_allow_html=True)

    st.markdown(spacer(24), unsafe_allow_html=True)

    # ── Metric Cards ─────────────────────────────────────────────────────────
    def _s(stats: dict, col: str, decimals: int = 0) -> str:
        if col not in stats:
            return "N/A"
        v = stats[col]["mean"]
        return f"{v:.{decimals}f}"

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(metric_card_dual(
            "Avg Calories", "🔥",
            _s(d_stats, "calories"), " kcal",
            _s(f_stats, "calories"), " kcal",
            note=f"Food is {round(f_stats['calories']['mean'] / d_stats['calories']['mean'], 1)}× higher"
                 if "calories" in d_stats and d_stats["calories"]["mean"] > 0 else "",
            note_positive=False,
        ), unsafe_allow_html=True)

    with c2:
        st.markdown(metric_card_dual(
            "Avg Protein", "💪",
            _s(d_stats, "protein_g", 1), " g",
            _s(f_stats, "protein_g", 1), " g",
            note=f"Avg fat {_s(d_stats, 'fat_g', 1)} g (drinks) · {_s(f_stats, 'fat_g', 1)} g (food)",
            note_positive=True,
        ), unsafe_allow_html=True)

    with c3:
        d_ratio = d_derived.get("fat_to_protein_ratio", "N/A")
        f_ratio = f_derived.get("fat_to_protein_ratio", "N/A")
        st.markdown(metric_card_dual(
            "Fat-to-Protein Ratio", "⚖️",
            str(d_ratio), " ratio",
            str(f_ratio), " ratio",
            note="Healthy threshold: ≤ 1.5",
            note_positive=False,
        ), unsafe_allow_html=True)

    import plotly.graph_objects as go
    import pandas as pd

    st.markdown(spacer(32), unsafe_allow_html=True)

    # ── Chart 1 — Macro Comparison (Grouped Bar Chart) ───────────────────────
    st.markdown(chart_header(
        "Macro Comparison: Drinks vs Food",
        "Average calories, protein, and net carbs side-by-side across both datasets",
    ), unsafe_allow_html=True)

    macro_cols = {"calories": "Avg Calories (kcal)", "protein_g": "Avg Protein (g)"}
    if "carb_g" in drinks_df.columns and "fiber_g" in drinks_df.columns:
        drinks_macro = drinks_df.copy()
        drinks_macro["net_carbs_g"] = (drinks_macro["carb_g"] - drinks_macro["fiber_g"]).clip(lower=0)
    else:
        drinks_macro = drinks_df.copy()
    if "carb_g" in food_df.columns and "fiber_g" in food_df.columns:
        food_macro = food_df.copy()
        food_macro["net_carbs_g"] = (food_macro["carb_g"] - food_macro["fiber_g"]).clip(lower=0)
    else:
        food_macro = food_df.copy()
    if "net_carbs_g" in drinks_macro.columns and "net_carbs_g" in food_macro.columns:
        macro_cols["net_carbs_g"] = "Avg Net Carbs (g)"

    macro_metrics = list(macro_cols.keys())
    drinks_avgs = [round(drinks_macro[c].mean(skipna=True), 1) if c in drinks_macro.columns else 0
                   for c in macro_metrics]
    food_avgs   = [round(food_macro[c].mean(skipna=True), 1) if c in food_macro.columns else 0
                   for c in macro_metrics]
    labels = [macro_cols[c] for c in macro_metrics]

    fig_macro = go.Figure([
        go.Bar(name="Drinks", x=labels, y=drinks_avgs,
               marker_color="#3ab26a", text=[f"{v:.1f}" for v in drinks_avgs],
               textposition="outside"),
        go.Bar(name="Food", x=labels, y=food_avgs,
               marker_color="#f4a261", text=[f"{v:.1f}" for v in food_avgs],
               textposition="outside"),
    ])
    fig_macro.update_layout(
        barmode="group",
        paper_bgcolor="#FAFAFA",
        plot_bgcolor="#FAFAFA",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(family="Inter, Arial, sans-serif"),
        yaxis=dict(gridcolor="#E5E5E5", title="Value"),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    st.plotly_chart(fig_macro, use_container_width=True)

    st.markdown(spacer(32), unsafe_allow_html=True)

    # ── Chart 2 — Top 5 Extremes (Horizontal Bar Chart, Food above Drinks) ───
    col_l, col_r = st.columns(2)

    def _top5_stacked_chart(metric: str, unit: str, fmt: str) -> go.Figure:
        """Food top-5 on top, Drinks top-5 below, separated by a gap row."""
        top_food = (
            food_df.dropna(subset=[metric])
            .nlargest(5, metric)[["item_name", metric]]
            .assign(group="Food")
            .sort_values(metric, ascending=True)
        )
        top_drink = (
            drinks_df.dropna(subset=[metric])
            .nlargest(5, metric)[["item_name", metric]]
            .assign(group="Drinks")
            .sort_values(metric, ascending=True)
        )
        stacked = pd.concat([top_drink, top_food], ignore_index=True)
        colors  = stacked["group"].map({"Drinks": "#3ab26a", "Food": "#f4a261"})

        fig = go.Figure(go.Bar(
            x=stacked[metric],
            y=stacked["item_name"],
            orientation="h",
            marker_color=colors,
            text=stacked[metric].apply(lambda v: f"{v:{fmt}} {unit}"),
            textposition="inside",
            customdata=stacked["group"],
            hovertemplate="%{y}<br>%{x:" + fmt + "} " + unit + " (%{customdata})<extra></extra>",
        ))
        for grp, col in [("Drinks", "#3ab26a"), ("Food", "#f4a261")]:
            fig.add_trace(go.Bar(
                x=[None], y=[None], orientation="h",
                name=grp, marker_color=col, showlegend=True,
            ))
        fig.add_shape(
            type="line", x0=0, x1=1, xref="paper", y0=4.5, y1=4.5, yref="y",
            line=dict(color="#cccccc", width=1, dash="dot"),
        )
        fig.add_annotation(
            x=0, xref="paper", y=4.5, yref="y",
            text="  ── Food ──", showarrow=False,
            font=dict(size=10, color="#f4a261"),
            xanchor="left", yanchor="bottom",
        )
        fig.add_annotation(
            x=0, xref="paper", y=4.5, yref="y",
            text="  ── Drinks ──", showarrow=False,
            font=dict(size=10, color="#3ab26a"),
            xanchor="left", yanchor="top",
        )
        fig.update_layout(
            paper_bgcolor="#FAFAFA",
            plot_bgcolor="#FAFAFA",
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(family="Inter, Arial, sans-serif"),
            xaxis=dict(gridcolor="#E5E5E5"),
            yaxis=dict(showgrid=False),
            showlegend=False,
            height=440,
        )
        return fig

    with col_l:
        st.markdown(chart_header("Top 5 Highest-Calorie Items"), unsafe_allow_html=True)
        st.plotly_chart(_top5_stacked_chart("calories", "kcal", ".0f"), use_container_width=True)

    with col_r:
        st.markdown(chart_header("Top 5 Highest-Protein Items"), unsafe_allow_html=True)
        st.plotly_chart(_top5_stacked_chart("protein_g", "g", ".1f"), use_container_width=True)
