"""
Drinks Analysis page.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.processor import compute_descriptive_stats, compute_derived_stats, COLUMN_LABELS
from app.components.cards import metric_card
from app.components.tables import style_inventory
from app.components.ui import chart_header, filter_label, insight_card, page_title, section_heading, spacer
from app.charts.drinks import macro_stacked_bar, insulin_spike_scatter
from app.utils.nutri_grade import score as nutri_score, GRADE_STYLE


def render() -> None:
    drinks_df = st.session_state.get("drinks_df")
    if drinks_df is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    groq_client = st.session_state.get("groq_client")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(page_title("Drink Nutrition Analysis"), unsafe_allow_html=True)

    # ── Quick Filters ─────────────────────────────────────────────────────────
    cal_max = int(drinks_df["calories"].max()) if "calories" in drinks_df.columns else 1000

    qf1, qf2, qf3 = st.columns([3, 2, 1], vertical_alignment="bottom")
    with qf1:
        st.markdown(filter_label("Quick Filters"), unsafe_allow_html=True)
        active_pills = st.pills(
            "drinks_quick_filters",
            ["🥑 Keto Friendly", "💪 Protein Boost", "🧂 Low Sodium"],
            selection_mode="multi",
            label_visibility="collapsed",
            key="d_pills",
        )
    with qf2:
        cal_range = st.slider("Calorie Range (kcal)", 0, cal_max, (0, cal_max), key="d_cal_range")
    with qf3:
        st.download_button(
            "⬇ Export Data",
            drinks_df.to_csv(index=False).encode(),
            file_name="drinks.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Apply Filters ─────────────────────────────────────────────────────────
    df = drinks_df.copy()
    if active_pills:
        if "🥑 Keto Friendly" in active_pills and "carb_g" in df.columns and "fiber_g" in df.columns:
            df = df[(df["carb_g"] - df["fiber_g"]).clip(lower=0) < 5]
        if "💪 Protein Boost" in active_pills and "protein_g" in df.columns:
            df = df[df["protein_g"] > 10]
        if "🧂 Low Sodium" in active_pills and "sodium_mg" in df.columns:
            df = df[df["sodium_mg"] < 50]
    if "calories" in df.columns:
        df = df[(df["calories"] >= cal_range[0]) & (df["calories"] <= cal_range[1])]
    df = df.reset_index(drop=True)

    st.caption(f"Showing **{len(df)}** of {len(drinks_df)} drinks")

    # ── Metric Cards ──────────────────────────────────────────────────────────
    stats   = compute_descriptive_stats(df)
    derived = compute_derived_stats(df)

    def _s(col: str, key: str = "mean", dec: int = 0) -> str:
        return f"{stats[col][key]:.{dec}f}" if col in stats else "N/A"

    avg_net_carb = derived.get("net_carb_mean_g")
    nc_val = f"{avg_net_carb:.1f}" if avg_net_carb is not None else "N/A"

    try:
        p_density = round(stats["protein_g"]["mean"] / stats["calories"]["mean"] * 100, 1) \
            if "protein_g" in stats and stats.get("calories", {}).get("mean", 0) > 0 else None
    except (KeyError, ZeroDivisionError):
        p_density = None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Avg Calories", "🔥", _s("calories"), "kcal"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(
            "Avg Sugar Proxy", "🍬", nc_val, "g",
            note="Avg net carbs (carbs − fiber)", note_positive=False,
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(
            "Avg Protein Density", "💪",
            str(p_density) if p_density is not None else "N/A", "g/100kcal",
            note="Protein per 100 kcal", note_positive=True,
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Avg Sodium", "🧂", _s("sodium_mg", "mean", 1), "mg"), unsafe_allow_html=True)

    st.markdown(spacer(16), unsafe_allow_html=True)

    # ── AI Insight ────────────────────────────────────────────────────────────
    llm_ok  = groq_client is not None and groq_client.is_available()
    insight = st.session_state.get("drinks_insight")

    if llm_ok:
        if insight:
            st.markdown(insight_card(insight), unsafe_allow_html=True)
        else:
            if st.button("✦ Generate AI Insight", key="d_gen_insight"):
                with st.spinner("Generating insight…"):
                    try:
                        from src.llm.summarizer import answer_query
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
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown(chart_header(
            "Macro Composition by Category",
            "% of total macro calories — net carbs, fat, protein",
        ), unsafe_allow_html=True)
        if "category" in df.columns and not df.empty:
            st.plotly_chart(macro_stacked_bar(df), use_container_width=True)
        else:
            st.info("Category data required for this chart.")

    with ch2:
        st.markdown(chart_header(
            "Insulin Spike Risk",
            "Total calories vs net carbs — higher = greater insulin response",
        ), unsafe_allow_html=True)
        if not df.empty:
            st.plotly_chart(insulin_spike_scatter(df), use_container_width=True)

    st.markdown(spacer(24), unsafe_allow_html=True)

    # ── Inventory Table ───────────────────────────────────────────────────────
    inv_l, inv_r = st.columns([4, 1])
    with inv_l:
        st.markdown(section_heading("Drink Inventory"), unsafe_allow_html=True)
    with inv_r:
        st.caption(f"Showing {len(df)} drinks")

    inv_df = df.copy()
    inv_df["Nutri-Grade"] = inv_df.apply(nutri_score, axis=1)

    display_cols = [c for c in
                    ["item_name", "category", "calories", "fat_g", "carb_g", "fiber_g", "protein_g", "sodium_mg"]
                    if c in inv_df.columns] + ["Nutri-Grade"]
    rename_map = {c: COLUMN_LABELS.get(c, c) for c in display_cols if c != "Nutri-Grade"}
    rename_map.update({"item_name": "Drink Name", "category": "Category"})

    display_df = inv_df[display_cols].rename(columns=rename_map)
    num_cols = display_df.select_dtypes(include="number").columns
    display_df[num_cols] = display_df[num_cols].round(1)
    display_df.index = range(1, len(display_df) + 1)

    num_col_config = {col: st.column_config.NumberColumn(col, format="%.1f") for col in num_cols}
    num_col_config["Nutri-Grade"] = st.column_config.TextColumn("Nutri-Grade", width="small")

    st.caption(
        "Nutri-Grade adapted from Singapore HPB standard (sugar proxy = net carbs; "
        "thresholds scaled to ~350 ml serving). Grade = worst of sugar and fat score."
    )
    st.dataframe(
        display_df.style.apply(style_inventory, grade_col="Nutri-Grade", grade_styles=GRADE_STYLE, axis=None),
        use_container_width=True,
        height=420,
        column_config=num_col_config,
    )

    st.download_button(
        "⬇ Download CSV",
        df.to_csv(index=False).encode(),
        file_name="drinks_filtered.csv",
        mime="text/csv",
    )
