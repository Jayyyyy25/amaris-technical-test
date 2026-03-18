"""Plotly chart factories for the Food Analysis page."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.charts import BASE_LAYOUT, MACRO_COLORS, _GRID
from app.utils.food_categories import CATEGORY_COLORS


def optimal_scatter(df: pd.DataFrame) -> go.Figure:
    """Scatter: Calories (X) vs Protein (Y), coloured by food category.
    Top-left quadrant = high protein, low calorie (optimal).
    """
    plot_df = df.dropna(subset=["calories", "protein_g"]).copy()

    fig = px.scatter(
        plot_df,
        x="calories",
        y="protein_g",
        color="food_category" if "food_category" in plot_df.columns else None,
        hover_name="item_name",
        hover_data={"calories": True, "protein_g": ":.1f", "food_category": False},
        labels={
            "calories":      "Total Calories (kcal)",
            "protein_g":     "Protein (g)",
            "food_category": "Category",
        },
        color_discrete_map=CATEGORY_COLORS,
    )
    fig.update_traces(marker=dict(size=9, opacity=0.85))

    med_cal = plot_df["calories"].median()
    med_pro = plot_df["protein_g"].median()
    fig.add_vline(x=med_cal, line_dash="dot", line_color="#9ca3af",
                  annotation_text="Median cal", annotation_position="top right")
    fig.add_hline(y=med_pro, line_dash="dot", line_color="#9ca3af",
                  annotation_text="Median protein", annotation_position="top right")

    fig.update_layout(
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(title="Category"),
        **BASE_LAYOUT,
    )
    return fig


def macro_distribution_bar(df: pd.DataFrame, n: int = 12) -> go.Figure:
    """Stacked bar: % of macro calories per nutrient for top N items by calories."""
    plot_df = df.dropna(subset=["calories", "fat_g", "carb_g", "protein_g"]).copy()
    plot_df = plot_df.nlargest(n, "calories")

    plot_df["fat_kcal"]     = plot_df["fat_g"]     * 9
    plot_df["carb_kcal"]    = plot_df["carb_g"]    * 4
    plot_df["protein_kcal"] = plot_df["protein_g"] * 4
    plot_df["total_kcal"]   = (
        plot_df["fat_kcal"] + plot_df["carb_kcal"] + plot_df["protein_kcal"]
    )

    for col, key in [("pct_fat", "fat_kcal"), ("pct_carb", "carb_kcal"),
                     ("pct_protein", "protein_kcal")]:
        plot_df[col] = (plot_df[key] / plot_df["total_kcal"] * 100).round(1)

    plot_df["short_name"] = plot_df["item_name"].str[:26]
    plot_df = plot_df.sort_values("pct_fat", ascending=False)

    fig = go.Figure()
    for label, col, color in [
        ("Fat",     "pct_fat",     MACRO_COLORS["Fat"]),
        ("Carbs",   "pct_carb",    MACRO_COLORS["Carbs"]),
        ("Protein", "pct_protein", MACRO_COLORS["Protein"]),
    ]:
        fig.add_trace(go.Bar(
            name=label,
            x=plot_df["short_name"],
            y=plot_df[col],
            marker_color=color,
            text=plot_df[col].apply(lambda v: f"{v:.0f}%"),
            textposition="inside",
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        yaxis=dict(title="% of Macro Calories", range=[0, 100], gridcolor=_GRID),
        xaxis=dict(title="", showgrid=False, tickangle=-30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        **BASE_LAYOUT,
    )
    return fig
