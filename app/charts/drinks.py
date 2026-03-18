"""Plotly chart factories for the Drinks Analysis page."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.charts import BASE_LAYOUT, MACRO_COLORS, _GRID


def macro_stacked_bar(df: pd.DataFrame) -> go.Figure:
    """Stacked bar: macro % of total macro calories per drink category."""
    plot_df = df.copy()
    plot_df["net_carb_g"] = (plot_df["carb_g"] - plot_df["fiber_g"]).clip(lower=0)

    agg = (
        plot_df.groupby("category")[["net_carb_g", "fat_g", "protein_g"]]
        .mean()
        .reset_index()
    )
    agg["carb_kcal"]    = agg["net_carb_g"] * 4
    agg["fat_kcal"]     = agg["fat_g"]      * 9
    agg["protein_kcal"] = agg["protein_g"]  * 4
    agg["total_kcal"]   = agg["carb_kcal"] + agg["fat_kcal"] + agg["protein_kcal"]

    for col, key in [("pct_carb", "carb_kcal"), ("pct_fat", "fat_kcal"), ("pct_protein", "protein_kcal")]:
        agg[col] = (agg[key] / agg["total_kcal"] * 100).round(1)

    agg = agg.sort_values("pct_carb", ascending=False)

    fig = go.Figure()
    for label, col, color in [
        ("Net Carbs", "pct_carb",    MACRO_COLORS["Net Carbs"]),
        ("Fat",       "pct_fat",     MACRO_COLORS["Fat"]),
        ("Protein",   "pct_protein", MACRO_COLORS["Protein"]),
    ]:
        fig.add_trace(go.Bar(
            name=label,
            x=agg["category"],
            y=agg[col],
            marker_color=color,
            text=agg[col].apply(lambda v: f"{v:.0f}%"),
            textposition="inside",
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        yaxis=dict(title="% of Total Macro Calories", range=[0, 100], gridcolor=_GRID),
        xaxis=dict(title="", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        **BASE_LAYOUT,
    )
    return fig


def insulin_spike_scatter(df: pd.DataFrame) -> go.Figure:
    """Scatter: Total Calories (X) vs Net Carbs (Y), coloured by drink category."""
    plot_df = df.copy()
    plot_df["net_carb_g"] = (plot_df["carb_g"] - plot_df["fiber_g"]).clip(lower=0)
    plot_df = plot_df.dropna(subset=["calories", "net_carb_g"])

    fig = px.scatter(
        plot_df,
        x="calories",
        y="net_carb_g",
        color="category" if "category" in plot_df.columns else None,
        hover_name="item_name",
        hover_data={"calories": True, "net_carb_g": ":.1f", "category": False},
        labels={
            "calories":    "Total Calories (kcal)",
            "net_carb_g":  "Net Carbs (g)",
            "category":    "Category",
        },
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8))
    fig.update_layout(
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(orientation="v", title="Category"),
        **BASE_LAYOUT,
    )
    return fig
