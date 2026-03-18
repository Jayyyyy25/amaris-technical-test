"""Shared Plotly layout constants used by all chart modules."""

_FONT = "Inter, Arial, sans-serif"
_BG   = "#FAFAFA"
_GRID = "#E5E5E5"

BASE_LAYOUT: dict = dict(
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family=_FONT),
    margin=dict(l=10, r=20, t=20, b=10),
)

MACRO_COLORS: dict[str, str] = {
    "Net Carbs": "#FFD166",
    "Fat":       "#EF476F",
    "Protein":   "#06D6A0",
    "Carbs":     "#FFD166",
}
