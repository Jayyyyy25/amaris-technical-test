"""
Food Analysis page.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processor import compute_descriptive_stats, compute_derived_stats, COLUMN_LABELS
from app.components.cards import metric_card
from app.components.tables import style_inventory
from app.charts.food import optimal_scatter, macro_distribution_bar
from app.utils.food_categories import assign as assign_category, PILL_MAP


def render() -> None:
    food_df_raw = st.session_state.get("food_df")
    if food_df_raw is None:
        st.info("Load the datasets using the sidebar to get started.")
        return

    groq_client = st.session_state.get("groq_client")

    food_df = food_df_raw.copy()
    food_df["food_category"] = food_df["item_name"].apply(assign_category)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-size:26px;font-weight:800;color:#1a1a1a;">'
        'Food Nutrition Analysis</h2>',
        unsafe_allow_html=True,
    )

    # ── Quick Filters ─────────────────────────────────────────────────────────
    cal_max = int(food_df["calories"].max()) if "calories" in food_df.columns else 1000

    qf1, qf2, qf3 = st.columns([3, 2, 1], vertical_alignment="bottom")
    with qf1:
        st.markdown('<p class="filter-label">Category Filter</p>', unsafe_allow_html=True)
        active_cats = st.pills(
            "food_category_filter",
            list(PILL_MAP.keys()),
            selection_mode="multi",
            label_visibility="collapsed",
            key="f_pills",
        )
    with qf2:
        cal_range = st.slider("Calorie Range (kcal)", 0, cal_max, (0, cal_max), key="f_cal_range")
    with qf3:
        st.download_button(
            "⬇ Export Data",
            food_df.to_csv(index=False).encode(),
            file_name="food.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Apply Filters ─────────────────────────────────────────────────────────
    df = food_df.copy()
    if active_cats:
        selected = [PILL_MAP[p] for p in active_cats if p in PILL_MAP]
        df = df[df["food_category"].isin(selected)]
    if "calories" in df.columns:
        df = df[(df["calories"] >= cal_range[0]) & (df["calories"] <= cal_range[1])]
    df = df.reset_index(drop=True)

    st.caption(f"Showing **{len(df)}** of {len(food_df)} food items")

    # ── Metric Cards ──────────────────────────────────────────────────────────
    stats   = compute_descriptive_stats(df)
    derived = compute_derived_stats(df)

    def _s(col: str, key: str = "mean", dec: int = 0) -> str:
        return f"{stats[col][key]:.{dec}f}" if col in stats else "N/A"

    try:
        protein = df["protein_g"] if "protein_g" in df.columns else pd.Series(0.0, index=df.index)
        fiber   = df["fiber_g"]   if "fiber_g"   in df.columns else pd.Series(0.0, index=df.index)
        cals    = df["calories"].replace(0, float("nan"))
        satiety_val = f"{round(float(((protein + fiber) / cals * 100).mean()), 1)}"
    except Exception:
        satiety_val = "N/A"

    ratio = derived.get("fat_to_protein_ratio", "N/A")
    is_ok = isinstance(ratio, (int, float)) and ratio <= 1.5

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Avg Calories", "🔥", _s("calories"), "kcal"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("Avg Protein", "💪", _s("protein_g", "mean", 1), "g"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(
            "Fat:Protein Ratio", "⚖️", str(ratio), "",
            note="✓ Within healthy threshold" if is_ok else "⚠ Above healthy threshold",
            note_positive=is_ok,
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card(
            "Avg Satiety Score", "🌿", satiety_val, "",
            note="(protein + fiber) / calories × 100",
            note_positive=True,
        ), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    # ── AI Insight ────────────────────────────────────────────────────────────
    llm_ok  = groq_client is not None and groq_client.is_available()
    insight = st.session_state.get("food_insight")

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
            if st.button("✦ Generate AI Insight", key="f_gen_insight"):
                with st.spinner("Generating insight…"):
                    try:
                        from src.summarizer import answer_query
                        drinks_df = st.session_state.get("drinks_df", pd.DataFrame())
                        st.session_state["food_insight"] = answer_query(
                            groq_client,
                            "In 2 sentences, highlight the most notable nutritional patterns in the food data.",
                            drinks_df, df,
                        )
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))

    # ── Charts ────────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Optimal Choice</div>
  <div class="chart-card-subtitle">Top-left = high protein, low calorie (best value)</div>
</div>
""", unsafe_allow_html=True)
        if not df.empty:
            st.plotly_chart(optimal_scatter(df), use_container_width=True)

    with ch2:
        st.markdown("""
<div class="chart-card">
  <div class="chart-card-title">Macro-Nutrient Distribution</div>
  <div class="chart-card-subtitle">% of macro calories — top 12 items by calorie count</div>
</div>
""", unsafe_allow_html=True)
        if not df.empty:
            st.plotly_chart(macro_distribution_bar(df, n=min(12, len(df))), use_container_width=True)

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ── Inventory Table ───────────────────────────────────────────────────────
    inv_l, inv_r = st.columns([4, 1])
    with inv_l:
        st.markdown(
            '<h3 style="font-size:20px;font-weight:700;color:#1a1a1a;margin:0 0 8px 0;">Food Inventory</h3>',
            unsafe_allow_html=True,
        )
    with inv_r:
        st.caption(f"Showing {len(df)} items")

    display_cols = [c for c in
                    ["item_name", "food_category", "calories", "fat_g", "carb_g", "fiber_g", "protein_g"]
                    if c in df.columns]
    rename_map = {c: COLUMN_LABELS.get(c, c) for c in display_cols}
    rename_map.update({"item_name": "Food Name", "food_category": "Category"})

    display_df = df[display_cols].rename(columns=rename_map)
    num_cols = display_df.select_dtypes(include="number").columns
    display_df[num_cols] = display_df[num_cols].round(1)
    display_df.index = range(1, len(display_df) + 1)

    num_col_config = {
        col: st.column_config.NumberColumn(col, format="%.1f")
        for col in num_cols
    }

    st.dataframe(
        display_df.style.apply(style_inventory, axis=None),
        use_container_width=True,
        height=420,
        column_config=num_col_config,
    )

    st.download_button(
        "⬇ Download CSV",
        df.to_csv(index=False).encode(),
        file_name="food_filtered.csv",
        mime="text/csv",
    )
