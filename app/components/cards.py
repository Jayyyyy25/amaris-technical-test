"""Shared metric card HTML components."""
from __future__ import annotations


def metric_card(
    title: str,
    icon: str,
    value: str,
    unit: str,
    note: str = "",
    note_positive: bool = True,
) -> str:
    """Single-value metric card (used on Drinks / Food pages)."""
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


def metric_card_dual(
    title: str,
    icon: str,
    d_val: str,
    d_unit: str,
    f_val: str,
    f_unit: str,
    note: str = "",
    note_positive: bool = True,
) -> str:
    """Two-column metric card showing Drinks vs Food values (used on Dashboard)."""
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
